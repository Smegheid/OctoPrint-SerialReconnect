# coding=utf-8

from __future__ import absolute_import

import octoprint.plugin
import time
from octoprint.util import RepeatedTimer, ResettableTimer

import os.path
from os import path

class SerialReconnectPlugin(octoprint.plugin.AssetPlugin,
                            octoprint.plugin.SettingsPlugin,
                            octoprint.plugin.ShutdownPlugin,
                            octoprint.plugin.StartupPlugin,
                            octoprint.plugin.TemplatePlugin):

  ####################################################
  # Private methods
  
  def __init__(self):
    # Timers used to handle initial startup delay (one-off resettable) and
    # poll serial connection to printer (repeat). Will initially be
    # started via on_after_startup().
    self._initial_timer = None
    self._poll_timer = None

    # Count of consecutive 'offline' status seen when polling.
    self._consec_offline = 0


  # Called if we've decided that the printer is disconnected and we need to reconnect
  # to its serial interface.
  def _reconnect(self):

    # Before poking at anything, get the current serial connection options.
    # This will retrieve whatever settings were previously st in the GUI
    # to connect to the printer, which we'll re-use again.
    serial = self._printer.get_connection_options()
    port = serial['portPreference']
    baud = serial['baudratePreference']

    # If the printer is set up with a particular serial port, then there's one thing
    # we can do to reduce the number of connection error notifications that we cause
    # with reconnect attempts. If the device node does not exist (USB-serial disappears
    # when unplugged or printer turned off) then don't bother even trying.
    if port and (port != 'AUTO'):
      if not path.exists(port):
        self._logger.info("Unable to reconnect: serial port %r not found." % port);
        return
      
    # Attempt to reconnect.
    self._logger.info("Reconnecting to printer on %r at %r baud" % (port, baud))
    self._printer.connect(port=port, baudrate=baud)


  # Called once per poll period to check up on the serial connection and reconnect
  # if disconnected.
  def _check_connection(self, num_offline):

    # At first glance, the reported states that we're interested in would appear to
    # be OFFLINE and OPERATIONAL. However, if the printer is off and a reconnection
    # attempt is made, the resulting failure to chooch will bump things over to an
    # ERROR state. _reconnect does attempt to avoid this for printers with a USB-serial
    # interface, but it might still crop up; for now, treat ERROR as the same as offline.
    status = self._printer.get_state_id()
    if(status == 'OFFLINE') or (status == 'ERROR'):
      self._consec_offline += 1
      self._logger.info("Printer disconnected (%r, %d of %d)"
                        % (status, self._consec_offline, num_offline))
    else:
      self._consec_offline = 0

    # If we've seen the printer consecutively offline for long enough, then
    # give the connection a kick.
    if(self._consec_offline >= num_offline):
      self._reconnect()

      # Start from scratch again, including any initial delay period to let things settle.
      self._restart_timer()


  # Starts the periodic timer. Assumes that the plugin is enabled and
  # that there is currently no periodic timer running.
  def _start_periodic_timer(self, poll_period, num_offline):
    self._logger.info("Starting connection polling timer at %r sec interval, reconnect after %r conseq. offline indications."
                      % (poll_period, num_offline))

    # Init the count of the number of consecutive printer offline states seen.
    self._consec_offline = 0
    
    # If we have a polling period configured, then start up our
    # periodic checks of the serial connection.
    if(poll_period > 0):
      self._poll_timer = RepeatedTimer(poll_period, self._check_connection, (num_offline,), run_first=True)
      self._poll_timer.start()


  # Stops any timers currently running.
  def _stop_timers(self):
    # Stop any initial startup delay timer. Important to do this
    # first, otherwise this might kick off another periodic timer
    # while we're messing with the poll timer.
    if self._initial_timer:
      self._initial_timer.cancel()
      self._initial_timer = None
      self._logger.debug("Stopped initial delay timer.")      

    # Connection polling timer.
    if self._poll_timer:
      self._poll_timer.cancel()
      self._poll_timer = None
      self._logger.debug("Stopped connection poll timer.")


  # Starts everything up again - stops any existing timer before kicking
  # off a new one.
  def _restart_timer(self):
    # Stop timers in progress.
    self._stop_timers()
    
    # Get the current settings.
    enabled = self._settings.get_boolean(['enabled']) 
    initial_delay = self._settings.get_int(['initial_delay'])
    poll_period = self._settings.get_int(['poll_period'])
    num_offline = self._settings.get_int(['num_offline'])

    self._logger.info("Restarting: enabled=%r, initial_delay=%r, poll_period=%r, num_offline=%r"
                       % (enabled, initial_delay, poll_period, num_offline))
      
    # If the plugin is enabled, then start up our periodic checks
    # of the serial connection after dealing with any initial delay.
    if(enabled == True):
      self._initial_timer = ResettableTimer(initial_delay, self._start_periodic_timer, (poll_period, num_offline,))
      self._initial_timer.start()
    else:
      self._logger.info("Checking is disabled. Not restarting.")

      
  ####################################################
  # Public methods

  # Plugin startup hook. Entry point that basically does nothing but
  # starts up our periodic timer for connection checks.
  def on_after_startup(self):
    self._logger.info("Plugin started.")
    self._restart_timer()

    
  # Enables plugin settings interface.  
  def get_template_configs(self):
    return [
      dict(type="settings", name="Serial Reconnect", custom_bindings=False)
      ]
  

  # Defaults when not previously configured.
  def get_settings_defaults(self):
      return dict(
        enabled=True,
        initial_delay=10, # Seconds before starting periodic poll. 
        poll_period=5,    # Seconds between polls.
        num_offline=3     # Consecutive offline indications before attempting reconnect.
      )


  # Hook called on first init of settings.
  def on_settings_initialized(self):
    self._logger.info("Settings initialised, restarting timer")
    self._restart_timer()


  # Hook called when settings saved. Mainly here to make sure the settings
  # we store are sane. *Should* be handled at the template level, but it's
  # cheap to double-check.
  def on_settings_save(self, data):
    # We'll allow the initial delay period to go as low as zero, but
    # no lower. We're not quite capable of time travel.
    if(data.get('initial_delay')):
      data['initial_delay'] = max(0, int(data['initial_delay']))

    # For the poll period, it really doesn't make much sense to
    # allow less than a 1 second period, otherwise we'll go berzerk.
    if(data.get('poll_period')):
      data['poll_period'] = max(1, int(data['poll_period']))

    # Same thing for the number of consecutive offline 
    if(data.get('num_offline')):
      data['num_offline'] = max(1, int(data['num_offline']))
      
    # Save the sanitised data.
    octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
    self._logger.info("Saved new settings: %r" % (data,))

    # Kick things off again with the new settings.
    self._restart_timer()


  # Software update hook. Largely boilerplate.
  def get_update_information(self):
    # Define the configuration for your plugin to use with the Software Update
    # Plugin here. See https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update
    # for details.
    return dict(
      updateSerialReconnect=dict(
        displayName="Serial Reconnect",
        displayVersion=self._plugin_version,
        
        # version check: github repository
        type="github_release",
        user="Smegheid",
        repo="OctoPrint-SerialReconnect",
        current=self._plugin_version,
        
        # update method: pip
        pip="https://github.com/Smegheid/OctoPrint-SerialReconnect/archive/{target_version}.zip"
      )
    )


# End of SerialReconnectPlugin class.
###################################

def __plugin_load__():
  global __plugin_implementation__
  __plugin_implementation__ = SerialReconnectPlugin()

  global __plugin_hooks__
  __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
  }

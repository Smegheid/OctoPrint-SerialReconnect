# OctoPrint-SerialReconnect

This is a simple Octoprint plugin that repeatedly attempts to re-esablish
the serial connection to a 3D printer when the connection is lost. The intent
is to simplify the case where an attached 3D printer is turned off and then
turned on again; by default, Octoprint will not reconnect to the printer
unless it is restarted.

This was originally a little cron-powered script written against Octoprint's
API to make things a little simpler for my daughter. The script would check
once per minute whether the printer had gone away, and if it found evidence
that it was back, it would reconnect. I wanted to better understand how plugins
work anyway, so I figured I'd rework it to comply with the plugin mechanism
and publish it. Hopefully it proves useful to someone.

It's worth noting that this has seen all of its testing against a couple of
Monoprice Mini Select v2 printers (one at work, one at home). It appears to
work well enough against that printer when run on an instance of OctoPi, but
this is the only hardware that it's been explicitly tested against. That said,
I wouldn't imagine that things would be too different with another printer;
the plugin doesn't do anything that's specific to the MP Mini, but instead
only pokes at Octoprint's printer connection API.

## Setup

Install via the bundled [Plugin Manager](https://github.com/foosel/OctoPrint/wiki/Plugin:-Plugin-Manager)
or manually using this URL:

    https://github.com/Smegheid/OctoPrint-SerialReconnect/archive/master.zip


## Configuration

Configuration is performed via a basic plugin settings interface (Settings ->
Plugins -> Serial Reconnect). Options include an checkbox control to enable
or disable checking completely, a couple of periods used in initial startup
and polling, and a threshold for the number of consecutive polls where the
printer is seen as disconnected before attempting a reconnect.

The defaults set by the plugin seem rasonable for an MP Select Mini, but
they may not play well with all other types of printer, so they're made
tweakable just in case.

## Notes

The biggest side-effect of this plugin is that it effectively renders
Octoprint's big (non-)red 'Disconnect' button useless (Side panel ->
Connection -> Disconnect) when enabled. Disconnecting manually puts
things in a state that doesn't look particularly different from the case
where the printer was turned off, so when the disconnect button is pressed,
the plugin then springs valiantly into action and helpfully reconnects the
printer. I haven't yet figured out a way to deal with this; if it's a
problem, I'd advise against installing this plugin for now.

This plugin is really only intended to deal with the case where the reason
the printer disconnected in the first place was because it was turned off.
If you're hoping to use this as a watchdog to automatically reconnect after
other problems occur, well, it might work, but I haven't tested against
any other use cases, and I have no idea if it'll work properly or not.

Finally, this has been tested alongside the MaylanConnectionFix plugin:

  https://plugins.octoprint.org/plugins/malyan_connection_fix/

This improves the repeatability of the initial connection to the MP
Select Mini (among other printers), and is definitely recommended if
you have one of these.
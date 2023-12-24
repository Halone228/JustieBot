from blinker import signal


notify_event = signal('notify-event')
expire_event = signal('expire-event')
add_event = signal('add-event')

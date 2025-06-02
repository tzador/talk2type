import rumps
import threading
import time
from Quartz import (
    CGEventTapCreate,
    kCGHIDEventTap,
    kCGHeadInsertEventTap,
    kCGEventKeyDown,
    kCGEventKeyUp,
    CGEventTapEnable,
    CGEventMaskBit,
    CGEventGetIntegerValueField,
    kCGKeyboardEventKeycode,
    CFMachPortCreateRunLoopSource,
    CFRunLoopAddSource,
    CFRunLoopGetCurrent,
    kCFRunLoopCommonModes,
)
from CoreFoundation import CFRunLoopRun

SPACEBAR = 49
HOLD_DURATION = 1.0  # 1 second


class Talk2TypeApp(rumps.App):
    def __init__(self):
        print("🚀 Initializing Talk2Type app...")
        super(Talk2TypeApp, self).__init__(
            "Talk2Type", icon="off.png", quit_button=None
        )
        self.menu = ["Toggle Icon", None, "Quit"]
        self.icon_state = False  # False: idle, True: active
        self.spacebar_pressed = False
        self.spacebar_start_time = None
        self.timer_thread = None
        print("📱 Menu bar app created with off.png icon")

        # Start keyboard monitor in separate thread
        print("🎹 Starting keyboard monitor thread...")
        threading.Thread(target=self.monitor_keys, daemon=True).start()

    def set_icon_green(self):
        if self.spacebar_pressed:  # Only activate if spacebar still held
            print("✅ 3 seconds reached - activating!")
            self.icon_state = True
            self.icon = "on.png"

    def update_icon(self):
        if self.spacebar_pressed:
            # Spacebar just pressed - start timer
            self.spacebar_start_time = time.time()
            print(f"⏰ Spacebar pressed - starting 3-second timer...")

            # Cancel any existing timer
            if self.timer_thread and self.timer_thread.is_alive():
                print("⏹️  Cancelling previous timer")

            # Start new 3-second timer
            self.timer_thread = threading.Timer(HOLD_DURATION, self.set_icon_green)
            self.timer_thread.start()

        else:
            # Spacebar released - deactivate immediately
            if self.timer_thread and self.timer_thread.is_alive():
                self.timer_thread.cancel()
                print("⏹️  Timer cancelled - spacebar released early")

            if self.icon_state:
                print("❌ Spacebar released - deactivating")
                self.icon_state = False
                self.icon = "off.png"

    def monitor_keys(self):
        print("🎯 Setting up keyboard event monitoring...")

        def callback(proxy, type_, event, refcon):
            keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
            is_down = type_ == kCGEventKeyDown

            # Only handle Spacebar
            if keycode == SPACEBAR:
                action = "DOWN" if is_down else "UP"
                print(f"🎯 SPACEBAR (keycode={keycode}) {action}")

                if is_down and not self.spacebar_pressed:
                    # Spacebar just pressed
                    self.spacebar_pressed = True
                    print("➕ Spacebar pressed - starting timer")
                    self.update_icon()

                elif not is_down and self.spacebar_pressed:
                    # Spacebar just released
                    self.spacebar_pressed = False
                    elapsed = (
                        time.time() - self.spacebar_start_time
                        if self.spacebar_start_time
                        else 0
                    )
                    print(f"➖ Spacebar released after {elapsed:.1f} seconds")
                    self.update_icon()

            return event

        print("🔧 Creating CGEventTap...")
        mask = CGEventMaskBit(kCGEventKeyDown) | CGEventMaskBit(kCGEventKeyUp)
        tap = CGEventTapCreate(
            kCGHIDEventTap, kCGHeadInsertEventTap, 0, mask, callback, None
        )

        if tap is None:
            print("❌ Failed to create event tap! Check Accessibility permissions.")
            print("📝 Go to: System Settings → Privacy & Security → Accessibility")
            print("📝 Add Terminal (or Python) and enable it")
            return
        else:
            print("✅ Event tap created successfully")

        print("🔗 Setting up run loop source...")
        source = CFMachPortCreateRunLoopSource(None, tap, 0)
        if source is None:
            print("❌ Failed to create run loop source")
            return
        else:
            print("✅ Run loop source created")

        CFRunLoopAddSource(CFRunLoopGetCurrent(), source, kCFRunLoopCommonModes)
        CGEventTapEnable(tap, True)
        print("✅ Keyboard monitoring active - listening for Spacebar...")
        print("🧪 Hold Spacebar for 3+ seconds to activate!")
        CFRunLoopRun()

    @rumps.clicked("Toggle Icon")
    def toggle_icon(self, _):
        print("🔄 Manual toggle icon clicked")
        self.icon_state = not self.icon_state
        icon_name = "on.png" if self.icon_state else "off.png"
        self.icon = icon_name
        print(f"🎯 Manually toggled icon to: {icon_name}")

    @rumps.clicked("Quit")
    def quit_app(self, _):
        print("👋 Quit button clicked - shutting down app")
        rumps.quit_application()


if __name__ == "__main__":
    print("🎬 Starting Talk2Type application...")
    Talk2TypeApp().run()

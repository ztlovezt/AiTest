class ScrcpyInput {
  constructor(callback, videoElement, width, height, debug = false) {
    this.callback = callback;
    this.width = width;
    this.height = height;
    this.debug = debug;
    this.videoElement = videoElement;
    this.pointerActive = false;
    this.pointerId = null;
    this.pointerX = 0;
    this.pointerY = 0;
    this.lastMouseMoveTime = 0;
    this.lastWheelTime = 0;
    this.MOUSE_MOVE_THROTTLE = 8;
    this.WHEEL_THROTTLE = 32;

    this.handlePointerDown = this.handlePointerDown.bind(this);
    this.handlePointerMove = this.handlePointerMove.bind(this);
    this.handlePointerUp = this.handlePointerUp.bind(this);
    this.handlePointerCancel = this.handlePointerCancel.bind(this);
    this.handleContextMenu = this.handleContextMenu.bind(this);
    this.handleWheel = this.handleWheel.bind(this);
    this.handleKeyDown = this.handleKeyDown.bind(this);
    this.handleKeyUp = this.handleKeyUp.bind(this);

    if (this.videoElement) {
      this.videoElement.style.touchAction = "none";
      this.videoElement.addEventListener("pointerdown", this.handlePointerDown);
      this.videoElement.addEventListener("pointermove", this.handlePointerMove);
      this.videoElement.addEventListener("contextmenu", this.handleContextMenu);
      this.videoElement.addEventListener("wheel", this.handleWheel, {
        passive: false,
      });
      this.videoElement.addEventListener("keydown", this.handleKeyDown);
      this.videoElement.addEventListener("keyup", this.handleKeyUp);
    }

    window.addEventListener("pointerup", this.handlePointerUp);
    window.addEventListener("pointercancel", this.handlePointerCancel);
  }

  resizeScreen(width, height) {
    this.width = width;
    this.height = height;
  }

  getVideoRect() {
    return this.videoElement ? this.videoElement.getBoundingClientRect() : null;
  }

  resolvePointerPosition(event) {
    const rect = this.getVideoRect();
    if (!rect) {
      return { x: 0, y: 0 };
    }
    const localX = Math.max(0, Math.min(event.clientX - rect.left, rect.width));
    const localY = Math.max(0, Math.min(event.clientY - rect.top, rect.height));
    return {
      x: (localX / Math.max(rect.width, 1)) * this.width,
      y: (localY / Math.max(rect.height, 1)) * this.height,
    };
  }

  handlePointerDown(event) {
    if (!this.videoElement || !this.videoElement.contains(event.target)) {
      return;
    }

    this.videoElement.focus();

    if (event.button === 2) {
      this.snedKeyCode(event, 0, 4);
      event.preventDefault();
      return;
    }

    if (event.button !== 0) {
      return;
    }

    const position = this.resolvePointerPosition(event);
    this.pointerActive = true;
    this.pointerId = event.pointerId;
    this.pointerX = position.x;
    this.pointerY = position.y;

    if (this.videoElement.setPointerCapture) {
      try {
        this.videoElement.setPointerCapture(event.pointerId);
      } catch (_) {
        // ignore
      }
    }

    const data = this.createTouchProtocolData(
      0,
      this.pointerX,
      this.pointerY,
      this.width,
      this.height,
      0,
      0,
      65535,
    );
    this.callback(data);
    event.preventDefault();
  }

  handlePointerMove(event) {
    if (!this.pointerActive || event.pointerId !== this.pointerId) {
      return;
    }

    const now = Date.now();
    if (now - this.lastMouseMoveTime < this.MOUSE_MOVE_THROTTLE) {
      event.preventDefault();
      return;
    }
    this.lastMouseMoveTime = now;

    const position = this.resolvePointerPosition(event);
    this.pointerX = position.x;
    this.pointerY = position.y;
    const data = this.createTouchProtocolData(
      2,
      this.pointerX,
      this.pointerY,
      this.width,
      this.height,
      0,
      0,
      65535,
    );
    this.callback(data);
    event.preventDefault();
  }

  releasePointer(event, sendBackKey = false) {
    if (sendBackKey && event.button === 2) {
      this.snedKeyCode(event, 1, 4);
      event.preventDefault();
      return;
    }

    if (!this.pointerActive) {
      return;
    }

    if (
      event.pointerId !== undefined &&
      this.pointerId !== null &&
      event.pointerId !== this.pointerId
    ) {
      return;
    }

    const position = this.resolvePointerPosition(event);
    this.pointerX = position.x;
    this.pointerY = position.y;
    const data = this.createTouchProtocolData(
      1,
      this.pointerX,
      this.pointerY,
      this.width,
      this.height,
      0,
      0,
      0,
    );
    this.callback(data);

    if (
      this.videoElement &&
      this.videoElement.releasePointerCapture &&
      this.pointerId !== null
    ) {
      try {
        this.videoElement.releasePointerCapture(this.pointerId);
      } catch (_) {
        // ignore
      }
    }

    this.pointerActive = false;
    this.pointerId = null;
    event.preventDefault();
  }

  handlePointerUp(event) {
    this.releasePointer(event, true);
  }

  handlePointerCancel(event) {
    this.releasePointer(event, false);
  }

  handleContextMenu(event) {
    event.preventDefault();
  }

  handleWheel(event) {
    const now = Date.now();
    if (now - this.lastWheelTime < this.WHEEL_THROTTLE) {
      event.preventDefault();
      return;
    }
    this.lastWheelTime = now;

    const rect = this.getVideoRect();
    if (!rect) {
      return;
    }

    const relativeX = Math.max(
      0,
      Math.min(event.clientX - rect.left, rect.width),
    );
    const relativeY = Math.max(
      0,
      Math.min(event.clientY - rect.top, rect.height),
    );
    const data = this.createScrollProtocolData(
      relativeX,
      relativeY,
      rect.width,
      rect.height,
      event.deltaX,
      event.deltaY,
      event.button || 0,
    );
    this.callback(data);
    event.preventDefault();
  }

  handleKeyDown(event) {
    if (
      event.altKey &&
      (event.key === "ArrowLeft" || event.key === "ArrowRight")
    ) {
      event.preventDefault();
      const direction = event.key === "ArrowLeft" ? "left" : "right";
      this.rotate(direction);
      return;
    }

    const androidKeyCode = this.mapToAndroidKeyCode(event);
    if (androidKeyCode !== null) {
      this.snedKeyCode(event, 0, androidKeyCode);
      event.preventDefault();
    }
  }

  handleKeyUp(event) {
    const androidKeyCode = this.mapToAndroidKeyCode(event);
    if (androidKeyCode !== null) {
      this.snedKeyCode(event, 1, androidKeyCode);
      event.preventDefault();
    }
  }

  mapToAndroidKeyCode(event) {
    const codeToAndroidKeyCode = {
      KeyA: 29,
      KeyB: 30,
      KeyC: 31,
      KeyD: 32,
      KeyE: 33,
      KeyF: 34,
      KeyG: 35,
      KeyH: 36,
      KeyI: 37,
      KeyJ: 38,
      KeyK: 39,
      KeyL: 40,
      KeyM: 41,
      KeyN: 42,
      KeyO: 43,
      KeyP: 44,
      KeyQ: 45,
      KeyR: 46,
      KeyS: 47,
      KeyT: 48,
      KeyU: 49,
      KeyV: 50,
      KeyW: 51,
      KeyX: 52,
      KeyY: 53,
      KeyZ: 54,
      Digit0: 7,
      Digit1: 8,
      Digit2: 9,
      Digit3: 10,
      Digit4: 11,
      Digit5: 12,
      Digit6: 13,
      Digit7: 14,
      Digit8: 15,
      Digit9: 16,
      Enter: 66,
      Backspace: 67,
      Tab: 61,
      Space: 62,
      Escape: 111,
      CapsLock: 115,
      NumLock: 143,
      ScrollLock: 116,
      ArrowUp: 19,
      ArrowDown: 20,
      ArrowLeft: 21,
      ArrowRight: 22,
      ShiftLeft: 59,
      ShiftRight: 60,
      ControlLeft: 113,
      ControlRight: 114,
      AltLeft: 57,
      AltRight: 58,
      MetaLeft: 117,
      MetaRight: 118,
      Numpad0: 144,
      Numpad1: 145,
      Numpad2: 146,
      Numpad3: 147,
      Numpad4: 148,
      Numpad5: 149,
      Numpad6: 150,
      Numpad7: 151,
      Numpad8: 152,
      Numpad9: 153,
      NumpadEnter: 160,
      NumpadAdd: 157,
      NumpadSubtract: 156,
      NumpadMultiply: 155,
      NumpadDivide: 154,
      F1: 131,
      F2: 132,
      F3: 133,
      F4: 134,
      F5: 135,
      F6: 136,
      F7: 137,
      F8: 138,
      F9: 139,
      F10: 140,
      F11: 141,
      F12: 142,
      Back: 4,
      Home: 3,
      Menu: 82,
    };

    const androidKeyCode = codeToAndroidKeyCode[event.code];
    return androidKeyCode !== undefined ? androidKeyCode : null;
  }

  snedKeyCode(keyevent, action, keycode) {
    const capsLockState = keyevent.getModifierState
      ? keyevent.getModifierState("CapsLock")
      : false;
    const numLockState = keyevent.getModifierState
      ? keyevent.getModifierState("NumLock")
      : false;

    let metakey = 0;
    if (keyevent.shiftKey) {
      metakey |= 0x40;
    }
    if (keyevent.ctrlKey) {
      metakey |= 0x2000;
    }
    if (keyevent.altKey) {
      metakey |= 0x10;
    }
    if (keyevent.metaKey) {
      metakey |= 0x20000;
    }
    if (capsLockState) {
      metakey |= 0x100000;
    }
    if (numLockState) {
      metakey |= 0x200000;
    }

    const data = this.createKeyProtocolData(
      action,
      keycode,
      keyevent.repeat || 0,
      metakey,
    );
    this.callback(data);
  }

  createTouchProtocolData(
    action,
    x,
    y,
    width,
    height,
    actionButton,
    buttons,
    pressure,
  ) {
    const type = 2;
    const buffer = new ArrayBuffer(1 + 1 + 8 + 4 + 4 + 2 + 2 + 2 + 4 + 4);
    const view = new DataView(buffer);
    let offset = 0;

    view.setUint8(offset, type);
    offset += 1;
    view.setUint8(offset, action);
    offset += 1;

    view.setUint8(offset, 0xff);
    offset += 1;
    view.setUint8(offset, 0xff);
    offset += 1;
    view.setUint8(offset, 0xff);
    offset += 1;
    view.setUint8(offset, 0xff);
    offset += 1;
    view.setUint8(offset, 0xff);
    offset += 1;
    view.setUint8(offset, 0xff);
    offset += 1;
    view.setUint8(offset, 0xff);
    offset += 1;
    view.setUint8(offset, 0xfd);
    offset += 1;

    view.setInt32(offset, Math.round(x), false);
    offset += 4;
    view.setInt32(offset, Math.round(y), false);
    offset += 4;
    view.setUint16(offset, Math.round(width), false);
    offset += 2;
    view.setUint16(offset, Math.round(height), false);
    offset += 2;
    view.setInt16(offset, pressure, false);
    offset += 2;
    view.setInt32(offset, actionButton, false);
    offset += 4;
    view.setInt32(offset, buttons, false);

    return buffer;
  }

  createKeyProtocolData(action, keycode, repeat, metaState) {
    const type = 0;
    const buffer = new ArrayBuffer(1 + 1 + 4 + 4 + 4);
    const view = new DataView(buffer);
    let offset = 0;

    view.setUint8(offset, type);
    offset += 1;
    view.setUint8(offset, action);
    offset += 1;
    view.setInt32(offset, keycode, false);
    offset += 4;
    view.setInt32(offset, repeat, false);
    offset += 4;
    view.setInt32(offset, metaState, false);

    return buffer;
  }

  createScrollProtocolData(x, y, width, height, hScroll, vScroll, button) {
    const type = 3;
    const buffer = new ArrayBuffer(1 + 4 + 4 + 2 + 2 + 2 + 2 + 4);
    const view = new DataView(buffer);
    let offset = 0;

    view.setUint8(offset, type);
    offset += 1;
    view.setInt32(offset, Math.round(x), false);
    offset += 4;
    view.setInt32(offset, Math.round(y), false);
    offset += 4;
    view.setUint16(offset, Math.round(width), false);
    offset += 2;
    view.setUint16(offset, Math.round(height), false);
    offset += 2;
    view.setInt16(
      offset,
      Math.max(-32768, Math.min(32767, Math.round(hScroll))),
      false,
    );
    offset += 2;
    view.setInt16(
      offset,
      Math.max(-32768, Math.min(32767, Math.round(vScroll))),
      false,
    );
    offset += 2;
    view.setInt32(offset, button, false);

    return buffer;
  }

  createScreenProtocolData(action) {
    const type = 4;
    const buffer = new ArrayBuffer(1 + 1);
    const view = new DataView(buffer);
    view.setUint8(0, type);
    view.setUint8(1, action);
    return buffer;
  }

  createPowerProtocolData(action) {
    const type = 7;
    const buffer = new ArrayBuffer(1 + 1);
    const view = new DataView(buffer);
    view.setUint8(0, type);
    view.setUint8(1, action);
    return buffer;
  }

  screen_on_off(action) {
    const data = this.createScreenProtocolData(action);
    this.callback(data);
  }

  rotate(direction) {
    const type = 100;
    const buffer = new ArrayBuffer(1 + 1);
    const view = new DataView(buffer);
    view.setUint8(0, type);
    view.setUint8(1, direction === "left" ? 0 : 1);
    this.callback(buffer);
  }

  destroy() {
    if (this.videoElement) {
      this.videoElement.removeEventListener(
        "pointerdown",
        this.handlePointerDown,
      );
      this.videoElement.removeEventListener(
        "pointermove",
        this.handlePointerMove,
      );
      this.videoElement.removeEventListener(
        "contextmenu",
        this.handleContextMenu,
      );
      this.videoElement.removeEventListener("wheel", this.handleWheel);
      this.videoElement.removeEventListener("keydown", this.handleKeyDown);
      this.videoElement.removeEventListener("keyup", this.handleKeyUp);
    }
    window.removeEventListener("pointerup", this.handlePointerUp);
    window.removeEventListener("pointercancel", this.handlePointerCancel);
    this.videoElement = null;
    this.callback = null;
    this.pointerActive = false;
    this.pointerId = null;
  }
}

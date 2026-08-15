/*
 * Barnaby — firmware for the physical companion.
 *
 * Base:  My Keepon (BeatBots), gutted and rewired.
 * Board: Arduino Nano / Pro Micro (any AVR with 2 PWM pins spare).
 *
 * Wiring
 *   D3   vibration motor    via NPN transistor + flyback diode (PWM)
 *   D4   TTP223 touch pad   under the felt on Barnaby's head, active HIGH
 *   D6   NeoPixel ring      the projector/scene light (8 or 12 px)
 *   D9   status LED         optional, mirrors jiggle state
 *
 * Protocol (115200 baud, newline-delimited ASCII) — mirrors keepon.py:
 *   host -> board            board -> host
 *   J <0-255>  jiggle        READY   on boot
 *   S          still         PET     touch sensor fired
 *   F <0-4>    face
 *   P <0-5>    scene
 *   C          celebrate
 *
 * The one behaviour that matters: once jiggling starts, only a human hand
 * stops it. There is no timeout on the motor, because a jiggle that gives up
 * on its own is just a notification with extra steps.
 */

#include <Adafruit_NeoPixel.h>

const uint8_t PIN_MOTOR  = 3;
const uint8_t PIN_TOUCH  = 4;
const uint8_t PIN_PIXELS = 6;
const uint8_t PIN_STATUS = 9;
const uint8_t NUM_PIXELS = 12;

Adafruit_NeoPixel pixels(NUM_PIXELS, PIN_PIXELS, NEO_GRB + NEO_KHZ800);

uint8_t  jiggleLevel = 0;      // 0 = still
uint8_t  face        = 0;
uint8_t  scene       = 0;
bool     lastTouch   = false;
uint32_t lastTouchMs = 0;
uint32_t phase       = 0;

const uint16_t DEBOUNCE_MS = 250;

void setup() {
  pinMode(PIN_MOTOR,  OUTPUT);
  pinMode(PIN_STATUS, OUTPUT);
  pinMode(PIN_TOUCH,  INPUT);
  pixels.begin();
  pixels.setBrightness(60);
  pixels.show();
  Serial.begin(115200);
  Serial.println("READY");
}

/* A flat PWM value feels like an appliance. Breathing it makes him feel
 * alive, which is the difference between being alerted and being nudged. */
void driveMotor() {
  if (jiggleLevel == 0) {
    analogWrite(PIN_MOTOR, 0);
    digitalWrite(PIN_STATUS, LOW);
    return;
  }
  float wave = (sin(phase / 120.0) + 1.0) / 2.0;      // 0..1, ~1.2s period
  uint8_t out = (uint8_t)(jiggleLevel * (0.55 + 0.45 * wave));
  analogWrite(PIN_MOTOR, out);
  digitalWrite(PIN_STATUS, HIGH);
}

void renderScene() {
  uint32_t c;
  switch (scene) {
    case 1:  c = pixels.Color(12, 10, 30);   break;  // dim — he's just here
    case 2:  c = pixels.Color(255, 170, 60); break;  // overture — tent goes up
    case 3:  c = pixels.Color(60, 90, 200);  break;  // focus — the long hill
    case 4:  c = pixels.Color(90, 200, 160); break;  // break — flat ground
    case 5:  c = pixels.Color(200, 110, 170); break; // curtain — the bow
    default: c = pixels.Color(0, 0, 0);      break;  // off — quiet mode
  }
  // Slow breathe so the room never reads as a status indicator.
  float b = scene == 0 ? 0.0 : 0.75 + 0.25 * (sin(phase / 400.0) + 1.0) / 2.0;
  for (uint8_t i = 0; i < NUM_PIXELS; i++) {
    pixels.setPixelColor(i, pixels.Color(
      (uint8_t)(((c >> 16) & 0xFF) * b),
      (uint8_t)(((c >> 8)  & 0xFF) * b),
      (uint8_t)((c & 0xFF) * b)));
  }
  pixels.show();
}

void celebrate() {
  for (uint8_t i = 0; i < 3; i++) {
    analogWrite(PIN_MOTOR, 140); delay(90);
    analogWrite(PIN_MOTOR, 0);   delay(70);
  }
}

void readTouch() {
  bool touched = digitalRead(PIN_TOUCH) == HIGH;
  if (touched && !lastTouch && (millis() - lastTouchMs) > DEBOUNCE_MS) {
    lastTouchMs = millis();
    jiggleLevel = 0;              // the hand is what stops him
    analogWrite(PIN_MOTOR, 0);
    Serial.println("PET");
  }
  lastTouch = touched;
}

void handleLine(String line) {
  line.trim();
  if (line.length() == 0) return;
  char cmd = line.charAt(0);
  int  arg = line.length() > 2 ? line.substring(2).toInt() : 0;

  switch (cmd) {
    case 'J': jiggleLevel = constrain(arg, 0, 255); break;
    case 'S': jiggleLevel = 0; break;
    case 'F': face  = constrain(arg, 0, 4); break;   // TODO: OLED face
    case 'P': scene = constrain(arg, 0, 5); break;
    case 'C': celebrate(); break;
  }
}

void loop() {
  while (Serial.available()) {
    handleLine(Serial.readStringUntil('\n'));
  }
  readTouch();
  driveMotor();
  if ((phase % 20) == 0) renderScene();
  phase++;
  delay(5);
}

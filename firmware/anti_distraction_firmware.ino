#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// --- Pitches Definition ---
#define NOTE_B0  31
#define NOTE_C1  33
#define NOTE_CS1 35
#define NOTE_D1  37
#define NOTE_DS1 39
#define NOTE_E1  41
#define NOTE_F1  44
#define NOTE_FS1 46
#define NOTE_G1  49
#define NOTE_GS1 52
#define NOTE_A1  55
#define NOTE_AS1 58
#define NOTE_B1  62
#define NOTE_C2  65
#define NOTE_CS2 69
#define NOTE_D2  73
#define NOTE_DS2 78
#define NOTE_E2  82
#define NOTE_F2  87
#define NOTE_FS2 93
#define NOTE_G2  98
#define NOTE_GS2 104
#define NOTE_A2  110
#define NOTE_AS2 117
#define NOTE_B2  123
#define NOTE_C3  131
#define NOTE_CS3 139
#define NOTE_D3  147
#define NOTE_DS3 156
#define NOTE_E3  165
#define NOTE_F3  175
#define NOTE_FS3 185
#define NOTE_G3  196
#define NOTE_GS3 208
#define NOTE_A3  220
#define NOTE_AS3 233
#define NOTE_B3  247
#define NOTE_C4  262
#define NOTE_CS4 277
#define NOTE_D4  294
#define NOTE_DS4 311
#define NOTE_E4  330
#define NOTE_F4  349
#define NOTE_FS4 370
#define NOTE_G4  392
#define NOTE_GS4 415
#define NOTE_A4  440
#define NOTE_AS4 466
#define NOTE_B4  494
#define NOTE_C5  523
#define NOTE_CS5 554
#define NOTE_D5  587
#define NOTE_DS5 623
#define NOTE_E5  659
#define NOTE_F5  698
#define NOTE_FS5 740
#define NOTE_G5  784
#define NOTE_GS5 831
#define NOTE_A5  880
#define NOTE_AS5 932
#define NOTE_B5  988
#define NOTE_C6  1047
#define NOTE_CS6 1109
#define NOTE_D6  1175
#define NOTE_DS6 1245
#define NOTE_E6  1319
#define NOTE_F6  1397
#define NOTE_FS6 1480
#define NOTE_G6  1568
#define NOTE_GS6 1661
#define NOTE_A6  1760
#define NOTE_AS6 1865
#define NOTE_B6  1976
#define NOTE_C7  2093
#define NOTE_CS7 2217
#define NOTE_D7  2349
#define NOTE_DS7 2489
#define NOTE_E7  2637
#define NOTE_F7  2794
#define NOTE_FS7 2960
#define NOTE_G7  3136
#define NOTE_GS7 3322
#define NOTE_A7  3520
#define NOTE_AS7 3729
#define NOTE_B7  3951
#define NOTE_C8  4186
#define NOTE_CS8 4435
#define NOTE_D8  4699
#define NOTE_DS8 4978
#define REST      0

// --- Configuration ---
#define SDA_PIN 21
#define SCL_PIN 22
#define BUZZER_PIN 18

LiquidCrystal_I2C lcd(0x27, 16, 2);

// ==========================================
// MELODY ARRAYS (Note, Duration format)
// Positive = standard note (4 = quarter, 8 = eighth)
// Negative = dotted note (-4 = dotted quarter = 1.5x duration)
// ==========================================

// --- Rickroll (Never Gonna Give You Up) ---
int rickroll_tempo = 114;
int rickroll[] = {
  NOTE_D5,-4, NOTE_E5,-4, NOTE_A4,4, 
  NOTE_E5,-4, NOTE_FS5,-4, NOTE_A5,16, NOTE_G5,16, NOTE_FS5,8,
  NOTE_D5,-4, NOTE_E5,-4, NOTE_A4,2,
  NOTE_A4,16, NOTE_A4,16, NOTE_B4,16, NOTE_D5,8, NOTE_D5,16,
  NOTE_D5,-4, NOTE_E5,-4, NOTE_A4,4,
  NOTE_E5,-4, NOTE_FS5,-4, NOTE_A5,16, NOTE_G5,16, NOTE_FS5,8,
  NOTE_D5,-4, NOTE_E5,-4, NOTE_A4,2,
  NOTE_A4,16, NOTE_A4,16, NOTE_B4,16, NOTE_D5,8, NOTE_D5,16
};
int rickroll_size = sizeof(rickroll) / sizeof(rickroll[0]) / 2;

// --- Imperial March (Star Wars) ---
int imperial_tempo = 120;
int imperial[] = {
  NOTE_A4,4, NOTE_A4,4, NOTE_A4,4, NOTE_F4,-8, NOTE_C5,16,
  NOTE_A4,4, NOTE_F4,-8, NOTE_C5,16, NOTE_A4,2,
  NOTE_E5,4, NOTE_E5,4, NOTE_E5,4, NOTE_F5,-8, NOTE_C5,16,
  NOTE_A4,4, NOTE_F4,-8, NOTE_C5,16, NOTE_A4,2
};
int imperial_size = sizeof(imperial) / sizeof(imperial[0]) / 2;

// --- Alone (Marshmello) ---
int alone_tempo = 130;
int alone[] = {
  NOTE_F4, 8, NOTE_F4, 8, NOTE_F4, 8, NOTE_F4, 8, NOTE_D4, 4,
  NOTE_G4, 8, NOTE_G4, 8, NOTE_G4, 8, NOTE_G4, 8, NOTE_E4, 4,
  NOTE_A4, 8, NOTE_A4, 8, NOTE_A4, 8, NOTE_A4, 8, NOTE_G4, 4
};
int alone_size = sizeof(alone) / sizeof(alone[0]) / 2;


// --- State Variables ---
char currentCommand = ' ';
int noteIndex = 0;             // Points to the NEXT note in the sequence
unsigned long nextEventTime = 0; // When to stop note or play next note

void setup() {
  Serial.begin(115200);
  Wire.begin(SDA_PIN, SCL_PIN);
  lcd.init();
  lcd.backlight();
  
  lcd.setCursor(0, 0);
  lcd.print("   LET'S STUDY   ");
  lcd.setCursor(0, 1);
  lcd.print("  be limitless  ");

  pinMode(BUZZER_PIN, OUTPUT);
}

void loop() {
  // 1. Listen for new commands
  if (Serial.available() > 0) {
    char cmd = Serial.read();
    if (cmd != currentCommand) {
      handleNewCommand(cmd);
      currentCommand = cmd;
      noteIndex = 0; 
      nextEventTime = millis(); // Start immediately
    }
  }

  // 2. Play melody (Non-blocking)
  if (millis() >= nextEventTime) {
    playNote();
  }
}

void handleNewCommand(char cmd) {
  lcd.clear();
  noTone(BUZZER_PIN);
  
  if (cmd == 'F') {
    lcd.setCursor(0, 0); lcd.print("Status: Focused");
    lcd.setCursor(0, 1); lcd.print("Nice work! :)");
  } 
  else if (cmd == 'D') {
    lcd.setCursor(0, 0); lcd.print("!!! RICKROLLED !!!");
    lcd.setCursor(0, 1); lcd.print("LOOK AT SCREEN!");
  } 
  else if (cmd == 'E') {
    lcd.setCursor(0, 0); lcd.print("!!! DANGER !!!");
    lcd.setCursor(0, 1); lcd.print("WAKE UP (IMP-M)");
  } 
  else if (cmd == 'A') {
    lcd.setCursor(0, 0); lcd.print("Status: Away");
    lcd.setCursor(0, 1); lcd.print("Alone - M-Mello ");
  } 
  else {
    lcd.setCursor(0, 0); lcd.print("Status: Idle");
    lcd.setCursor(0, 1); lcd.print("No face detected");
  }
}

void playNote() {
  if (currentCommand == 'F' || currentCommand == 'I' || currentCommand == ' ') {
    noTone(BUZZER_PIN);
    return;
  }

  int* melody;
  int melodySize;
  int tempo;

  if (currentCommand == 'D') {
    melody = rickroll; melodySize = rickroll_size; tempo = rickroll_tempo;
  } 
  else if (currentCommand == 'E') {
    melody = imperial; melodySize = imperial_size; tempo = imperial_tempo;
  } 
  else if (currentCommand == 'A') {
    melody = alone; melodySize = alone_size; tempo = alone_tempo;
  } else {
    return;
  }

  if (noteIndex >= melodySize) {
    noteIndex = 0; // Loop the sequence
  }

  // Calculate note duration (in ms) formulas
  int wholenote = (60000 * 4) / tempo;
  int divider = melody[noteIndex * 2 + 1];
  int noteDuration = 0;
  
  if (divider > 0) {
    noteDuration = wholenote / divider;
  } else if (divider < 0) {
    noteDuration = wholenote / abs(divider);
    noteDuration *= 1.5; // dotted note
  }

  int frequency = melody[noteIndex * 2];

  if (frequency != REST) {
    tone(BUZZER_PIN, frequency, noteDuration * 0.9); // Only play for 90%
  } else {
    noTone(BUZZER_PIN);
  }

  // Advance index and schedule next note
  nextEventTime = millis() + noteDuration;
  noteIndex++;
}

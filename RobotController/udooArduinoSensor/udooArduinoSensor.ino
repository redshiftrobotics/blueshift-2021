float convertAnalog(float a) {
  return a * (5.0 / 1023.0);
}

void setup() {
  Serial.begin(9600);
}

float ampMult = 0.0732;
float voltMult = 0.2423;

void loop() {
  float amps = convertAnalog(analogRead(A0)) * ampMult;
  float volts = convertAnalog(analogRead(A1)) * voltMult;

  Serial.print(amps);
  Serial.print(",");
  Serial.print(volts);
  Serial.println("\n");

  delay(100);
}
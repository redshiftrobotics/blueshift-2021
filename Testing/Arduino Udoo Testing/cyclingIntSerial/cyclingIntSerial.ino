/*
 * This code is mean to run on the Arduino built into the UDOO Bolt to read sensor data and send it to python
 * Right now, it just sends a number between 0 and 31 instead of actual sensor data
 */
// the setup routine runs once when you press reset:
void setup() {
  // initialize serial communication at 9600 bits per second:
  Serial.begin(9600);
}

float ampMult = 0.0732;
float voltMult = 0.2423;

// the loop routine runs over and over again forever:
void loop() {
  // read the input on analog pin 0:
  float amps = analogRead(A0) * ampMult;
  float volts = analogRead(A1) * voltMult;
  // print out the value you read:
  //Serial.print("[");
  Serial.print(amps);
  Serial.print(",");
  Serial.print(volts);
  //Serial.print("]");
  Serial.println("\n");
  delay(100);        // delay in between reads for stability
}

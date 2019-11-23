/*
  AnalogReadSerial

  Reads an analog input on pin 0, prints the result to the Serial Monitor.
  Graphical representation is available using Serial Plotter (Tools > Serial Plotter menu).
  Attach the center pin of a potentiometer to pin A0, and the outside pins to +5V and ground.

  This example code is in the public domain.

  http://www.arduino.cc/en/Tutorial/AnalogReadSerial
*/

// the setup routine runs once when you press reset:
void setup() {
  // initialize serial communication at 9600 bits per second:
  Serial.begin(9600);
}

int cycleTest = 0;

// the loop routine runs over and over again forever:
void loop() {
  // read the input on analog pin 0:
//  int sensorValue = analogRead(A0);
  // print out the value you read:
  cycleTest ++;
  if (cycleTest == 31) cycleTest = 0;
  Serial.print(cycleTest);
  delay(100);        // delay in between reads for stability
}

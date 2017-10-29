#define PD_OP  A0
#define LED_PWR   7

int i;

void setup() {
  analogReference(EXTERNAL);
  pinMode(LED_PWR, OUTPUT);
  pinMode(PD_OP, INPUT);
  Serial.begin(115200);
}

void loop() {
  digitalWrite(LED_PWR, HIGH);
  for(i=0;i<20;i++)
  {
    Serial.print("1024");
    Serial.print("\t");
    Serial.println(analogRead(PD_OP));
    delay(50);
  }
  digitalWrite(LED_PWR, LOW);
  for(i=0;i<20;i++)
  {
    Serial.print("0");
    Serial.print("\t");
    Serial.println(analogRead(PD_OP));
    delay(50);
  }
}

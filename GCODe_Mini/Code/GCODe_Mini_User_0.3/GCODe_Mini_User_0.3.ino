#define PD_OP  A0
#define LED_PWR   7
#define echo 0

float readout[2];
void oversample(int ms, int delayms, float *ret);

void setup() {
analogReference(EXTERNAL);
pinMode       (LED_PWR, OUTPUT);
digitalWrite  (LED_PWR, LOW);
pinMode       (PD_OP, INPUT);

Serial.begin(115200);
}

void loop() {
  if(Serial.available()) {
    String req = Serial.readStringUntil('\n');
    
    #if echo
    Serial.println(req);
    Serial.flush();
    #endif
    
    if (req.indexOf("READ") >= 0) 
    {
      int sampleTime = req.substring(4).toInt();
      if (sampleTime > 0)
      {
        oversample(sampleTime,100, readout);
        
        Serial.print(readout[0]);
        Serial.print("\t");
        Serial.println(readout[1]);
      }
      else
      Serial.println("INVALID FORMAT: READ N(ms)");
    }

    else if (req.indexOf("LED") >= 0)
    {
      if      (req.indexOf("ON")  >=0) {
        pinMode(LED_PWR, INPUT);
      }
      else if (req.indexOf("OFF") >=0) {
        digitalWrite(LED_PWR, LOW);
        pinMode(LED_PWR, OUTPUT);
      }
      else    Serial.println("INVALID FORMAT: LED ON/OFF");
    }

    else if (req.indexOf("ID") >= 0)
    {
     
      Serial.println("ABODe V1.1");
    }

    else if (req.indexOf("FW") >= 0)
    {
      Serial.println("0.2");
    }
    
    else Serial.println("INVALID REQUEST");

  Serial.flush();
  }
}

void oversample(int ms, int delayms, float *ret)
{
  float i=0,
        i2=0;

  long reading, n = ms/delayms;

  unsigned long startTime = millis();
  
  while (millis() - startTime < ms)
  {
    reading = analogRead(A0);
    i += reading;
    i2 = i2 + reading*reading;
    delay(delayms);
  }

  i = i/n;
  i2 = i2/n;

  ret[0] = i;
  ret[1] = sqrt(abs(i*i - i2));
}

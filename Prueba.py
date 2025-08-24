import requests, uvicorn, json
from fastapi import FastAPI, Form, Response
from twilio.twiml.messaging_response import MessagingResponse
  

bot_app = FastAPI()

def formatOutput(Body, data):
    
    if 'error' not in data:
        data_output = json.dumps(data['nutritions'])
        data_output = data_output.replace(" ", "") #remove whitespaces
    else:
        data_output = json.dumps(data)
        data_output = data_output.replace(":", "\n") #create paragraphs

    data_output = data_output.replace('"', '') #get only the nutrition information
    data_output = data_output.replace(",", "\n") #create paragraphs
    data_output = data_output.replace("{","").replace("}", "") #remove brackets
    
    data_output = Body +"\n \n" + data_output #add the header

    return data_output


def getInfoFruit(fruit_name):

    fruit_name = fruit_name.lower()
    url = 'https://fruityvice.com/api/fruit/{}'.format(fruit_name)
    resp = requests.get(url)
    if resp.status_code != 200:
        return {"error": "not a fruit"}
    data = resp.json()
    
    return data 

@bot_app.post("/bot")
async def chat(Body: str = Form(...)):
   
    data = getInfoFruit(Body)
    output = formatOutput(Body, data)
    response = MessagingResponse()
    msg = response.message(output)

    return Response(content=str(response), media_type="application/xml")


if __name__ == "__main__":
    uvicorn.run(bot_app, host="0.0.0.0", port=5000)
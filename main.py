import websockets
import asyncio
import json
import random
import ssl
import pathlib

conf=json.loads(open("config.json",encoding="utf8").read())
maxa=conf["maxstrenth"]["a"]
maxb=conf["maxstrenth"]["b"]
mina=conf["minstrenth"]["a"]
minb=conf["minstrenth"]["b"]
dgip=conf["ip"]
if maxa<mina or maxb<minb:
    print("https://www.baidu.com/s?ie=UTF-8&wd=%E6%AF%94%E8%BE%83%E5%A4%A7%E5%B0%8F")
    exit()

dgconnect=False
clients=set()
strentha=strenthb=usernum=0
async def dgupdate():
    global strentha,strenthb,dgconnect
    try:
        async with websockets.connect("ws://"+dgip+":23301") as dg:
            await dg.send('{"id": 1,"method": "queryStrength"}')
            recv=json.loads(await dg.recv())
        if recv['id']==1:
            strentha=recv['data']['totalStrengthA']-9
            strenthb=recv['data']['totalStrengthB']-9
            print('-->'+str(recv))
            dgconnect=True
    except:
        dgconnect=False

async def addstrenth(place,strenth):
    if strenth>10 or strenth<-10:
        return
    global strentha,strenthb,maxa,maxb,mina,minb
    if place:
        if strentha+strenth>maxa or strentha+strenth<mina:
            return False
    else:
        if strenthb+strenth>maxb or strenthb+strenth<minb:
            return False
    if strenth>10 or strenth<-10:
        return False
    id=random.randint(2,1145141919810)
    try:
        async with websockets.connect("ws://"+dgip+":23301") as dg:
            await dg.send(json.dumps({"id": id,"method": "addStrength","data": {"channel": place, "strength": strenth}}))
            recv=json.loads(await dg.recv())
        print('-->'+str(recv))
        return
    except:
        return

async def server(websocket):
    global dgconnect,maxa,maxb,mina,minb,strentha,strenthb,usernum,clients,conf
    try:
        async for message in websocket:
            clients.add(websocket)
            recv=json.loads(message)
            print('< '+message)
            usernum=len(clients)
            await dgupdate()
            if recv['type']=='init':
                send=json.dumps({'type': 'init','data': {
                    'serverconn': dgconnect,
                    'maxa': maxa,
                    'maxb': maxb,
                    'mina': mina,
                    'minb': minb,
                    'strentha': strentha,
                    'strenthb': strenthb,
                    'usernum': usernum,
                    'anote': conf["note"]["a"],
                    'bnote': conf["note"]["b"]
                }})
                print(send)
                websockets.broadcast(clients,send)
            elif recv['type']=='addstrenth':
                await addstrenth(recv['data']['side'],recv['data']['strenth'])
                send=json.dumps({'type': 'update','data': {
                    'serverconn': dgconnect,
                    'strentha': strentha,
                    'strenthb': strenthb,
                    'usernum': usernum,
                }})
                print('> '+str(send))
                websockets.broadcast(clients,send)
    finally:
        if websocket in clients:
            clients.remove(websocket)

async def main():
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    pem = pathlib.Path(__file__).with_name(conf["cert"])
    ssl_context.load_cert_chain(pem)
    async with websockets.serve(server, "0.0.0.0", 8443,ssl=ssl_context):
        await asyncio.Future()

asyncio.run(dgupdate())
asyncio.run(main())
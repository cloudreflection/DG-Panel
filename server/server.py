import websockets
import yaml
import requests

import asyncio
import json
import ssl
import pathlib
import uuid
import logging
import random
import time

config = yaml.load(
    open("server\\config.yml", encoding="utf8").read(), yaml.Loader)
if config["panel"]["admin_token"] == None:
    config["panel"]["admin_token"] = uuid.uuid4()


logging.basicConfig(
    format='%(asctime)s[%(levelname)s] %(message)s', level=logging.INFO)


def chkadmin(token):
    if token == config["panel"]["admin_token"]:
        return True
    else:
        return False


ipcache = {}
id = 0  # xie


def ip(ip):
    global ipcache, id
    if ip in ipcache:
        if time.time()-ipcache[ip]["time"] < 5:
            return False
        else:
            ipcache[ip]["time"] = time.time()
            return ipcache[ip]
    id += 1
    try:
        co = json.loads(requests.get(
            f"http://ip-api.com/json/{ip}?fields=status,countryCode").text)
        if co["status"] == "success":
            ipcache[ip] = {
                "time": time.time(), "co": co["countryCode"], "id": id}
            return ipcache[ip]["co"]
        else:
            ipcache[ip] = {"time": time.time(), "co": 0, "id": id}
            return ipcache[ip]
    except:
        ipcache[ip] = {"time": time.time(), "co": 0, "id": id}
        return ipcache[ip]


class dungeon:
    list_full = {"a": [], "b": []}

    def addtask(self, data, ipinfo):
        if data["time"] > config["dungeon"]["maxtime"] or data["time"] <= 0 or type(data["wave"]) != int:
            return
        if data['strenth'] > config['dungeon'][data['side']]['maxstrenth'] or data['strenth'] > config['dungeon'][data['side']]['maxstrenth']:
            return
        data["delay"] = random.randint(0, 10)
        data["status"] = 0
        data["user"] = "user"+ipinfo["id"]
        data["country"] = ipinfo["co"]
        self.list_full["side"].append(data)

    def rmtask(self, data):
        del self.list_full[data["side"]][0]

    def runtask(self, data):
        self.list_full[data["side"]][0]['status'] = 1
        self.list_full[data["side"]][0]['runtime'] = time.time()

    def getlist(self):
        list = {"a": self.list_full['a'][0:config["panel"]['max_show']-1],
                "b": self.list_full['b'][0:config["panel"]['max_show']-1]}
        return list


dg = dungeon()
clients = set()
deviceconn = False


async def server(websocket):
    try:
        async for message in websocket:
            global clients, deviceconn
            logging.info(websocket.remote_address[0]+" : "+message)
            clients.add(websocket)
            try:
                recv = json.loads(message)
            except:
                await websocket.send(json.dumps({'code': 250, 'msg': 'SB?'}))
                return
            if recv.get('type', False) == 'init':
                msg = json.dumps({"code": 0, 'online': len(
                    clients), 'connect': deviceconn, 'list': dg.getlist(), 'setting': config['dungeon']})
                websockets.broadcast(clients, msg)  # type: ignore
                logging.info('broadcast: '+msg)
                continue
            elif recv.get('type', False) == 'isadmin':
                if chkadmin(recv['token']):
                    msg = {'code': 2, 'msg': 'success'}
                    logging.warning('New admin login')
                else:
                    msg = {'code': 100, 'msg': 'Wrong token'}
                    logging.warning('Admin login failed:Wrong token')
                await websocket.send(json.dumps(msg))
                continue
            elif recv.get('type', False) == 'addtask':
                ipinfo = ip(websocket.remote_address[0])
                if ipinfo == False:
                    continue
                dg.addtask(recv['data'], ipinfo)
            elif chkadmin(recv.get('token')) == False:
                continue
            elif recv.get('type', False) == 'rmtask':
                dg.rmtask(recv['data'])
            elif recv.get('type', False) == 'runtask':
                dg.runtask(recv['data'])
            elif recv.get('type', False) == "device":
                deviceconn = recv['status']
            else:
                continue
            msg = json.dumps({"code": 1, 'online': len(
                clients), 'list': dg.getlist(), 'device': deviceconn})
            websockets.broadcast(clients, json.dumps(msg))  # type: ignore
            logging.info('broadcast: '+msg)
    finally:
        if websocket in clients:
            clients.remove(websocket)


async def main():
    if config["panel"].get('cert', None) == None:
        ssl_context = None
    else:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(pathlib.Path(
            __file__).with_name(config["panel"]["cert"]))
    print(f'''

Connect link: {'ws' if config["panel"]["cert"]==None else 'wss'}://[your ip]:{config["panel"]["port"]}
Admin link: {'ws' if config["panel"]["cert"]==None else 'wss'}://[your ip]:{config["panel"]["port"]}#{config["panel"]["admin_token"]}

''')
    async with websockets.serve(server, config["panel"]["listen"], config["panel"]["port"], ssl=ssl_context):  # type: ignore
        await asyncio.Future()

asyncio.run(main())

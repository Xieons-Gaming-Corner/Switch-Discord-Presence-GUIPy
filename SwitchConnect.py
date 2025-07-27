import argparse
import sys
import json
import socket
import struct
import time
import re
import requests
from pypresence import Presence

TCP_PORT = 0xCAFE
PACKETMAGIC = 0xFFAADD23

parser = argparse.ArgumentParser()
parser.add_argument('ip', help='The IP address of your device')
parser.add_argument('client_id', help='The Client ID of your Discord Rich Presence application')
parser.add_argument('--ignore-home-screen', dest='ignore_home_screen', action='store_true', help='Don\'t display the home screen. Defaults to false if missing this flag.')

questOverrides = None
switchOverrides = None

try: 
    questOverrides = json.loads(requests.get("https://raw.githubusercontent.com/Sun-Research-University/PresenceClient/master/Resource/QuestApplicationOverrides.json").text)
    switchOverrides = json.loads(requests.get("https://raw.githubusercontent.com/Sun-Research-University/PresenceClient/master/Resource/SwitchApplicationOverrides.json").text)
except:
    print('Failed to retrieve Override files')
    exit()

#Defines a title packet
class Title:

    def __init__(self, raw_data):
        unpacker = struct.Struct('2Q612s')
        enc_data = unpacker.unpack(raw_data)
        self.magic = int(enc_data[0])
        if int(enc_data[1]) == 0:
            self.pid = int(enc_data[1])
            self.name = 'Home Menu'
        else:
            self.pid = int(enc_data[1])
            self.name = enc_data[2].decode('utf-8', 'ignore').split('\x00')[0]
        if int(enc_data[0]) == PACKETMAGIC:
            if self.name in questOverrides:
                if questOverrides[self.name]['CustomName'] != '':
                    self.name = questOverrides[self.name]['CustomName']
        else:
            if self.name in switchOverrides:
                if switchOverrides[self.name]['CustomName'] != '':
                    self.name = switchOverrides[self.name]['CustomName']



def main():
    consoleargs = parser.parse_args()

    switch_ip = consoleargs.ip
    client_id = consoleargs.client_id

    if not checkIP(switch_ip):
        print('Invalid IP')
        exit()

    rpc = Presence(str(client_id))
    try:
        rpc.connect()
        rpc.clear()
        connected = True
    except:
        print('Unable to start RPC!')
        connected = False

    switch_server_address = (switch_ip, TCP_PORT)

    def connect_socket():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while True:
            try:
                sock.connect(switch_server_address)
                print('Successfully connected to %s' % repr(switch_server_address))
                
                return sock
            except:
                time.sleep(1)

    sock = connect_socket()

    lastProgramName = ''
    startTimer = 0
    last_data_time = time.time()

    while True:
        try:
            sock.settimeout(2)  # таймаут ожидания данных
            data = sock.recv(628)
            if not data:
                # Соединение разорвано
                raise ConnectionResetError
            last_data_time = time.time()  # обновляем таймер получения данных
        except socket.timeout:
            # Не получали данных более 5 секунд — считаем устройство пропавшим
            print('No data received for 5 seconds. Assuming device is offline.')
            try:
                rpc.clear()
            except:
                pass
            sock.close()
            sock = connect_socket()
            continue
        except Exception as e:
            # Ошибка соединения или чтения — переподключение
            print(f'Connection error: {e}. Reconnecting...')
            try:
                rpc.clear()
            except:
                pass
            sock.close()
            sock = connect_socket()
            continue

        # Обработка полученных данных
        title = Title(data)
        if title.magic == PACKETMAGIC:
            if lastProgramName != title.name:
                startTimer = int(time.time())
            
            # Обработка ситуации с невозможностью подключиться к устройству
            if not connected:
                # Если ранее не было соединения, значит попытка подключиться удалась — сбрасываем таймер
                try:
                    startTimer = 0
                    rpc.clear()
                except:
                    pass
                connected = True

            if consoleargs.ignore_home_screen and title.name == 'Home Menu':
                rpc.clear()
                connected = False  # считаем, что устройство "отключено" или в состоянии без игры
            else:
                # Обновление статуса (оставшийся код)
                smallimagetext = ''
                largeimagekey = ''
                details = ''
                largeimagetext = title.name
                if title.name == 'Home Menu':
                    largeimagekey = 'switch'
                    details = 'Navigating the Home Menu'
                    largeimagetext = 'Home Menu'
                    smallimagetext = 'On the Switch'
                elif int(title.pid) != PACKETMAGIC:
                    smallimagetext = 'SwitchPresence-Rewritten'
                    if title.name not in switchOverrides:
                        largeimagekey = iconFromPid(title.pid)
                        details = str(title.name)
                    else:
                        orinfo = switchOverrides[title.name]
                        largeimagekey = orinfo['CustomKey'] or iconFromPid(title.pid)
                        details = orinfo['CustomPrefix'] or 'Playing'
                        details += ' ' + title.name
                else:
                    smallimagetext = 'QuestPresence'
                    if title.name not in questOverrides:
                        largeimagekey = title.name.lower().replace(' ', '')
                        details = 'Playing ' + title.name
                    else:
                        orinfo = questOverrides[title.name]
                        largeimagekey = orinfo['CustomKey'] or title.name.lower().replace(' ', '')
                        details = orinfo['CustomPrefix'] or 'Playing'
                        details += ' ' + title.name

                if not title.name:
                    title.name = ''
                
                lastProgramName = title.name

                try:
                    rpc.update(details=details, large_image=largeimagekey,
                               large_text=largeimagetext, small_text=smallimagetext)
                    # Успешное обновление — считаем, что устройство активно и есть игра
                    connected = True
                except Exception as e_update:
                    print(f'Error updating RPC: {e_update}')
                    # Если ошибка обновления RPC — можно считать устройство "отключенным"
                    try:
                        rpc.clear()
                    except:
                        pass
                    connected = False

            time.sleep(1)
            
# uses regex to validate ip
def checkIP(ip):
    regex = r'''^(25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.(
            25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.( 
            25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.( 
            25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)$'''
    return re.search(regex, ip)

def iconFromPid(pid):
    return '0' + str(hex(int(pid))).split('0x')[1]


if __name__ == '__main__':
    main()
            

#!/usr/bin/env python

from concurrent.futures import ThreadPoolExecutor
from requests import ConnectTimeout, Session, Response, get

from bs4 import BeautifulSoup, NavigableString, Tag


ROOT_PATH = 'http://192.168.66.1/cgi-bin/luci'
UNKNOWN_SERVICE_UUID = '47AE43EA-A913-450C-8F2C-7EF90886B1A6'
GREEN_LED_TOGGLE_CHRCT = 'DF61B1EC-AF8E-43F2-8D46-A0EFE0AEFCFF'
RED_LED_TOGGLE_CHRCT = '55DE3C3A-6E85-4046-9672-A48465D4C489'

def check_connection() -> None:
    '''Make an attempt to detect the router.'''

    try:
        response = get(ROOT_PATH)
        if response.status_code == 403:
            print('\nThe router has been detected. The connection is success.\n')
    except ConnectTimeout:
        print(f'\nConnection timeout.\nThe router has not been founded in your network, or it has the web page address different from {ROOT_PATH}.\n')
        exit()

def logging(session: Session) -> bool:
    check_connection()

    print('Enter the user name and the password to control devices connected to the router.')

    for _ in range(2):
        user_name = input('Enter the user name: ')
        password = input('Enter the password: ')

        response = session.post(ROOT_PATH, params={
            'luci_username': user_name,
            'luci_password': password
        })
        if response.ok:
            return True
        else:
            print('Incorrect user name and password.')

    print('\nYou need to know the correct user name and password to control devices connected to the router.')
    return False

def print_dic(dev_info: dict[int, dict[str, str]]) -> None:
    for dev_num, name_mac in dev_info.items():
        print(
            f'#{dev_num}.\n'
            f'The device\'s name: {name_mac['dev_name']};\n'
            f'The device\'s MAC address: {name_mac['dev_mac']}.'
        )

def prepare_devices_info() -> dict[int, dict[str, str]]:
    devices_num = 0
    while True:
        try:
            devices_num = int(input('\nEnter the number of devices to connect to: '))
            break
        except ValueError:
            print('This is not a number.')

    dev_info: dict[int, dict[str, str]] = {}
    for i in range(devices_num):
        while True:
            dev_name = input(f'Enter the name of the device #{i+1}: ')
            if dev_name:
                break

        dev_mac = input(f'Enter the MAC address of the device #{i+1}. If you do not know it press "Enter": ')
        dev_info[i+1] = {'dev_name': dev_name, 'dev_mac': dev_mac}

    print('\nThe information about devices you have entered:')
    print_dic(dev_info)

    return dev_info

def search_for_mac(response: Response, dev_name: str) -> str:
    parser = BeautifulSoup(response.content, 'html.parser')

    dev_name_input_field: Tag = parser.find('input', {'value': dev_name}) # type: ignore
    dev_name_cell: Tag = dev_name_input_field.parent.parent # type: ignore
    dev_row: Tag = dev_name_cell.find_previous_sibling('div', attrs={'data-name': 'ble_addr'}) # type: ignore
    dev_addr_input_field: Tag = dev_row.find('div').find('input') # type: ignore
    dev_address = str(dev_addr_input_field.attrs['value'])

    return dev_address

def search_for_devices(session: Session, dev_info: dict[int, dict[str, str]]) -> bool:
    '''Get the list of the detected Bluetooth devices (IOT Services → Bluetooth)'''

    response = session.get(ROOT_PATH+'/admin/dusun/bul')
    devices_list = response.text

    for dev_num, name_mac in list(dev_info.items()):
        if name_mac['dev_name'] not in devices_list:
            dev_info.pop(dev_num)
    if not dev_info:
        return False

    for name_mac in dev_info.values():
        if not name_mac['dev_mac']:
            name_mac['dev_mac'] = search_for_mac(response, name_mac['dev_name'])

    print('\nThe information about devices which was founded:')
    print_dic(dev_info)

    return True

def get_device_by_mac(session: Session, dev_info: dict[int, dict[str, str]], dev_num: int) -> None:
    response: Response | dict[str, dict[str, int]] = session.get(
        ROOT_PATH+'/admin/dusun/bul/device',
        params={'mac': dev_info[dev_num]['dev_mac']}
    )
    if response.status_code != 200:
        dev_info.pop(dev_num)
        print(f'The connection to the device {dev_info[dev_num]['dev_name']} {dev_info[dev_num]['dev_mac']} has failed.')
        return

    while True:
        response = session.get(
            ROOT_PATH+'/admin/dusun/bul/device/status',
            params={'mac': dev_info[dev_num]['dev_mac']}
        ).json()
        if response['data']['connect_status'] == 1: # type: ignore
            print(f'You have connected to the device {dev_info[dev_num]['dev_name']} {dev_info[dev_num]['dev_mac']}.')
            break

def connect_to_devices(session: Session, dev_info: dict[int, dict[str, str]]) -> bool:
    # https://www.squash.io/how-to-parallelize-a-simple-python-loop/
    with ThreadPoolExecutor() as executor:
        for dev_num in list(dev_info):
            executor.submit(get_device_by_mac, session, dev_info, dev_num)

    print('\nThe information about devices you have connected to:')
    print_dic(dev_info)

    return len(dev_info) != 0

def toggle_led(session: Session, dev_mac: str, color: str) -> int:
    chrct = RED_LED_TOGGLE_CHRCT
    if color == 'green':
        chrct = GREEN_LED_TOGGLE_CHRCT

    return session.get(
        ROOT_PATH+'/admin/dusun/bul/device/operation',
        params={
            'op': 'Write',
            'mac': dev_mac,
            'service': UNKNOWN_SERVICE_UUID,
            'characteristic': chrct,
            'data': 1
        }
    ).status_code

def enter_device_number(dev_info_len: int) -> int:
    if dev_info_len == 1:
        return 1

    while True:
        try:
            dev_choice = int(input('\nEnter the device number you want to control: '))
            if 0 < dev_choice <= dev_info_len:
                break
        except ValueError:
            print('This is not a number, or this number is out of the bounds.')

    return dev_choice

def control_menu(session: Session, dev_info: dict[int, dict[str, str]]):
    while True:
        dev_choice = enter_device_number(len(dev_info))

        print(
            '\n1. Toggle the green LED.\n'
            + '2. Toggle the red LED.\n'
            + '3. Choose another device.\n'
            + '4. Exit from the program.'
        )
        dev_chrct = int(input('Enter the command number: '))
        match dev_chrct:
            case 1:
                status = toggle_led(session, dev_info[dev_choice]['dev_mac'], 'green')

                if status == 200:
                   print(f'You have just toggled the green LED at {dev_info[dev_choice]['dev_name']} {dev_info[dev_choice]['dev_mac']}.')
                else:
                    print(f'Something goes wrong while toggling the green LED at {dev_info[dev_choice]['dev_name']} {dev_info[dev_choice]['dev_mac']}.')
            case 2:
                status = toggle_led(session, dev_info[dev_choice]['dev_mac'], 'red')

                if status == 200:
                   print(f'You have just toggled the red LED at {dev_info[dev_choice]['dev_name']} {dev_info[dev_choice]['dev_mac']}.')
                else:
                    print(f'Something goes wrong while toggling the red LED at {dev_info[dev_choice]['dev_name']} {dev_info[dev_choice]['dev_mac']}.')
            case 4:
                exit()
            case _:
                continue

def main_session() -> None:
    with Session() as session:
        if not logging(session):
            exit()

        dev_info = prepare_devices_info()
        if not dev_info:
            print('\nIt has been chosen less than 1 device to connect to.')
            exit()

        devices_founded = search_for_devices(session, dev_info)
        if not devices_founded:
            print('\nYour devices have not been founded.')
            exit()

        at_least_one_connected = connect_to_devices(session, dev_info)
        if not at_least_one_connected:
            print('\nFailed to connect to any of the devices.')
            exit()

        control_menu(session, dev_info)

if __name__ == '__main__':
    main_session()
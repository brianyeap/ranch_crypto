import json
import requests

from django.shortcuts import render, redirect
from django.http import JsonResponse

OCTA = 10 ** 8
API_URL = "https://fullnode.devnet.sui.io/"
# http://34.70.238.35:9000


# Helper functions
def get_transactions(address):
    get_transactions_url = API_URL

    get_transactions_payload = json.dumps([
        {
            "method": "sui_getTransactionsByInputObject",
            "jsonrpc": "2.0",
            "params": [
                address
            ],
            "id": "1"
        }
    ])

    get_transactions_headers = {
        'content-type': 'application/json',
    }

    get_transactions_response = requests.request("POST", get_transactions_url, headers=get_transactions_headers,
                                                 data=get_transactions_payload)
    return get_transactions_response.json()


def get_object(object_id):
    get_object_url = API_URL

    get_object_payload = json.dumps([
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "sui_getObject",
            "params": [
                object_id
            ]
        }
    ])

    get_object_headers = {
        'content-type': 'application/json',
    }

    get_object_response = requests.request("POST", get_object_url, headers=get_object_headers,
                                           data=get_object_payload)
    return get_object_response.json()


def get_transaction_info(param_data):
    get_transaction_info_url = API_URL

    get_transaction_info_payload = param_data

    get_transaction_info_headers = {
        'Content-Type': 'application/json'
    }

    get_transaction_response = requests.request("POST", get_transaction_info_url, headers=get_transaction_info_headers,
                                                data=get_transaction_info_payload)
    return get_transaction_response.json()


def get_price_data(pool_id):
    try:
        address_txs = get_transactions(pool_id)[0]['result']
        object_data = get_object(pool_id)[0]['result']['details']['data']['fields']
        transaction_info_payloads = []

        temp_array = []
        price_data_array = []
        for address_tx_count in range(0, (len(address_txs))):
            if not address_tx_count % 2000 and address_tx_count != 0:
                transaction_info_payloads.append(temp_array)
                temp_array = []
            elif address_tx_count == len(address_txs) - 1:
                transaction_info_payloads.append(temp_array)
                temp_array = []
            temp_array.append(json.loads(json.dumps({
                "jsonrpc": "2.0",
                "id": address_tx_count,
                "method": "sui_getTransaction",
                "params": [
                    address_txs[address_tx_count][1]
                ]
            })))

        open_candle_timestamp = 0
        open_price = 0
        next_candle_timestamp = 0
        candle_array = []
        candle_temp_array = []
        for transaction_info_payload in transaction_info_payloads:
            transaction_infos = get_transaction_info(json.dumps(transaction_info_payload))

            for transaction_info in transaction_infos:
                if 'events' in str(transaction_info):

                    # Transaction ID
                    transaction_id = transaction_info['result']['certificate']['transactionDigest']

                    # timestamp
                    timestamp_ms = transaction_info['result']['timestamp_ms']

                    # get token x and y
                    transaction_info_typeArguments = \
                        transaction_info['result']['certificate']['data']['transactions'][0]['Call']['typeArguments']
                    token_x = transaction_info_typeArguments[0].rsplit('::', 1)[1]
                    token_y = transaction_info_typeArguments[1].rsplit('::', 1)[1]

                    transaction_info_events = transaction_info['result']['effects']['events']
                    transaction_info_move_event = transaction_info_events[len(transaction_info_events) - 1]['moveEvent']
                    if 'SwapTokenEvent' in transaction_info_move_event['type']:
                        transaction_info_move_event_fields = transaction_info_move_event['fields']
                        sender = transaction_info_move_event['sender']

                        try:
                            processed_array = []
                            if transaction_info_move_event['fields']['x_to_y']:
                                # Sell
                                transaction_type = 'sell'
                                out_amount = float(transaction_info_move_event_fields['out_amount'])
                                in_amount = float(transaction_info_move_event_fields['in_amount']) / OCTA
                                price = round(out_amount / in_amount, 2)
                            else:
                                # Buy
                                transaction_type = 'buy'
                                out_amount = float(transaction_info_move_event_fields['out_amount']) / OCTA
                                in_amount = float(transaction_info_move_event_fields['in_amount'])
                                price = round(in_amount / out_amount, 2)

                            if open_candle_timestamp == 0:
                                open_candle_timestamp = timestamp_ms
                                open_price = price
                                next_candle_timestamp = timestamp_ms + 60000

                                candle_temp_array.append({"timestamp": open_candle_timestamp, "price": price})
                            elif next_candle_timestamp >= timestamp_ms:
                                candle_temp_array.append({"timestamp": open_candle_timestamp, "price": price})
                            else:
                                # [timestamp, open, high, low, close]
                                processed_array = [timestamp_ms, open_price,
                                                   max(candle_temp_array, key=lambda x: x['price'])["price"],
                                                   min(candle_temp_array, key=lambda x: x['price'])["price"], price]

                                candle_array.append(candle_temp_array)
                                candle_temp_array = []
                                open_candle_timestamp = 0

                            price_data_dict = {
                                "token_x": token_x,
                                "token_y": token_y,
                                "lp_x": object_data['x'],
                                "lp_y": object_data['y'],
                                'transaction_id': transaction_id,
                                "timestamp": timestamp_ms,
                                "address": sender,
                                "type": transaction_type,
                                "in_amount": in_amount,
                                "out_amount": out_amount,
                                "price": price,
                                "processed_array": processed_array
                            }

                            price_data_array.append(price_data_dict)
                        except ZeroDivisionError:
                            pass
    except TypeError:
        return []

    return price_data_array


# API
def get_price(request, pool_id):
    data = get_price_data(pool_id)
    return JsonResponse(data, safe=False)


def home(request):
    # Temp data: 0x594be91376504256f4427df4c4e38eb578aa2857
    return redirect('price_chart', '0x594be91376504256f4427df4c4e38eb578aa2857')


def price_chart(request, pool_id):
    return render(request, "main/price_chart.html")

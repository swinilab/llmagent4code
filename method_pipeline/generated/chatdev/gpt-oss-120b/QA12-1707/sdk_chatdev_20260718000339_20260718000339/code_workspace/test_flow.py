import urllib.request, json
BASE='http://0.0.0.0:8001'

def post(path, data):
    data_bytes = json.dumps(data).encode()
    req = urllib.request.Request(BASE+path+'/', data=data_bytes, method='POST', headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)

def main():
    cust = post('/customers', {'name':'Alice','address':'123 St','phone':'555','banking_details':'bank123'})
    print('Customer', cust)
    prod = post('/products', {'description':'Widget','unit_price':9.99,'currency':'USD','quantity':10})
    print('Product', prod)
    order = post('/orders', {'customer_id':cust['id'],'items':[{'product_id':prod['id'],'quantity':2}]})
    print('Order', order)
    # review accept
    data = json.dumps({'accept': True}).encode()
    req = urllib.request.Request(f"{BASE}/orders/{order['id']}/review/", data=data, method='POST', headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req) as resp:
        reviewed = json.load(resp)
    print('Reviewed', reviewed)
    inv = post('/invoices', {'order_id':order['id'],'billing_info':'Alice Billing','due_in_days':10})
    print('Invoice', inv)
    pay = post('/payments', {'order_id':order['id'],'amount':inv['amount'],'method':'card'})
    print('Payment', pay)
    # ship
    req = urllib.request.Request(f"{BASE}/shipping/{order['id']}/", method='POST')
    with urllib.request.urlopen(req) as resp:
        print('Shipping response', resp.status)

if __name__=='__main__':
    main()

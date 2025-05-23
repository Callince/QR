import razorpay

razorpay_client = None

def init_razorpay(app):
    global razorpay_client
    razorpay_client = razorpay.Client(
        auth=(app.config['RAZORPAY_KEY_ID'], app.config['RAZORPAY_KEY_SECRET'])
    )
    return razorpay_client
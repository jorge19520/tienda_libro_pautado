import os
import requests
import smtplib
from email.message import EmailMessage
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables
load_dotenv()

PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
PDF_DRIVE_LINK = os.getenv("PDF_DRIVE_LINK")

# Change to https://api-m.paypal.com for production
PAYPAL_API_BASE = "https://api-m.sandbox.paypal.com"  

app = FastAPI(title="Tienda de Libros Digitales API (PayPal)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class OrderRequest(BaseModel):
    order_id: str

def get_paypal_access_token():
    """Generates an OAuth 2.0 access token for PayPal API."""
    url = f"{PAYPAL_API_BASE}/v1/oauth2/token"
    headers = {"Accept": "application/json", "Accept-Language": "en_US"}
    data = {"grant_type": "client_credentials"}
    
    response = requests.post(url, auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET), headers=headers, data=data)
    
    if response.status_code != 200:
        print(f"Failed to get PayPal token: {response.text}")
        raise Exception("Could not authenticate with PayPal")
        
    return response.json()["access_token"]


def send_delivery_email(customer_email: str):
    """Sends the email with the Google Drive link."""
    try:
        msg = EmailMessage()
        msg['Subject'] = '¡Gracias por tu compra! Aquí tienes tu Libro Pautado'
        msg['From'] = SENDER_EMAIL
        msg['To'] = customer_email
        
        # HTML Content
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
                    <h2 style="color: #2c3e50; text-align: center;">¡Gracias por tu pago mediante PayPal!</h2>
                    <p>Hola,</p>
                    <p>Hemos confirmado tu pago de forma exitosa. Aquí tienes el enlace para acceder a tu libro electrónico pautado (Iglesia de Dios Israelita).</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{PDF_DRIVE_LINK}" style="background-color: #3498db; color: white; padding: 15px 25px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px;">
                            Descargar / Ver Libro PDF
                        </a>
                    </div>
                    <p style="font-size: 14px; color: #7f8c8d;">Si tienes algún problema para acceder al enlace, no dudes en responder a este correo.</p>
                    <br>
                    <p>Saludos cordiales,<br>El equipo de la Tienda de Libros Digitales</p>
                </div>
            </body>
        </html>
        """
        msg.set_content("Por favor activa HTML para ver este mensaje.")
        msg.add_alternative(html_content, subtype='html')

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
            
        print(f"Email successfully sent to {customer_email}")
    except Exception as e:
        print(f"Error sending email: {e}")


@app.post("/create-paypal-order")
async def create_paypal_order():
    """Creates a new order in PayPal and returns the order ID for the frontend to approve."""
    try:
        access_token = get_paypal_access_token()
        url = f"{PAYPAL_API_BASE}/v2/checkout/orders"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        
        # Create an order for $200.00 MXN
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "amount": {
                        "currency_code": "MXN",
                        "value": "200.00"
                    },
                    "description": "Libro Pautado - Iglesia de Dios Israelita"
                }
            ]
        }
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code not in (200, 201):
            raise HTTPException(status_code=400, detail=response.json())
            
        return response.json()
        
    except Exception as e:
        print(f"Error creating order: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/capture-paypal-order")
async def capture_paypal_order(order: OrderRequest, background_tasks: BackgroundTasks):
    """Captures the payment after the user approves it on the frontend."""
    try:
        access_token = get_paypal_access_token()
        url = f"{PAYPAL_API_BASE}/v2/checkout/orders/{order.order_id}/capture"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        
        response = requests.post(url, headers=headers)
        data = response.json()
        
        if response.status_code in (200, 201) and data["status"] == "COMPLETED":
            # Extract the payer's email to send the book
            customer_email = data.get("payer", {}).get("email_address")
            
            if customer_email:
                print(f"Payment successful for {customer_email}. Sending email...")
                background_tasks.add_task(send_delivery_email, customer_email)
            else:
                print("Payment successful, but no email returned from PayPal.")
                
            return {"status": "success", "message": "Payment captured successfully"}
        else:
            print(f"Failed to capture order: {data}")
            raise HTTPException(status_code=400, detail="Failed to capture the payment")
            
    except Exception as e:
        print(f"Error capturing order: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

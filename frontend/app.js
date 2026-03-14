document.addEventListener('DOMContentLoaded', () => {
    const loadingSpinner = document.getElementById('loading-spinner');
    const notificationArea = document.getElementById('notification-area');
    const notificationMessage = document.getElementById('notification-message');
    const closeNotificationBtn = document.getElementById('close-notification');

    closeNotificationBtn.addEventListener('click', () => {
        notificationArea.classList.add('hidden');
    });

    function setLoading(isLoading) {
        if (isLoading) {
            loadingSpinner.classList.remove('hidden');
        } else {
            loadingSpinner.classList.add('hidden');
        }
    }

    function showNotification(message, type) {
        notificationMessage.textContent = message;
        notificationArea.className = `notification ${type}`;
        notificationArea.classList.remove('hidden');
        
        setTimeout(() => {
            notificationArea.classList.add('hidden');
        }, 8000);
    }

    // Initialize PayPal Smart Buttons
    if (window.paypal) {
        paypal.Buttons({
            // Call your server to set up the transaction
            createOrder: async function(data, actions) {
                try {
                    // Update this URL if your render app name is different
                    const response = await fetch('https://tienda-libro-backend.onrender.com/create-paypal-order', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    });

                    const orderData = await response.json();

                    if (!orderData.id) {
                        throw new Error(orderData.detail || 'Failed to create order. Verifique que configuró el Client ID en backend/.env');
                    }

                    return orderData.id;
                } catch (error) {
                    console.error("Error creating order:", error);
                    showNotification(error.message, 'error');
                }
            },

            // Call your server to finalize the transaction
            onApprove: async function(data, actions) {
                setLoading(true);
                try {
                    // Update this URL if your render app name is different
                    const response = await fetch('https://tienda-libro-backend.onrender.com/capture-paypal-order', {
                        method: 'POST',
                        body: JSON.stringify({
                            order_id: data.orderID
                        }),
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    });

                    const result = await response.json();

                    if (response.ok && result.status === "success") {
                        showNotification('¡Pago exitoso mediante PayPal! Hemos enviado el PDF a su correo.', 'success');
                    } else {
                        throw new Error(result.detail || 'Fallo al capturar el pago.');
                    }
                } catch (error) {
                    console.error("Error capturing order:", error);
                    showNotification('El pago no pudo ser procesado o verificado correctamente.', 'error');
                } finally {
                    setLoading(false);
                }
            },
            
            onError: function (err) {
                console.error("PayPal Error:", err);
                showNotification('Hubo un error al comunicarse con PayPal.', 'error');
            },

            onCancel: function (data) {
                showNotification('Pago cancelado.', 'error');
            }

        }).render('#paypal-button-container');
    } else {
        showNotification('Error: El SDK de PayPal no pudo cargar. Verifique el Client ID en index.html', 'error');
    }
});

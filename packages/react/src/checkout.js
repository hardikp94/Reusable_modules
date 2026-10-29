let scriptPromise;
export function loadRazorpay(documentImpl = globalThis.document, windowImpl = globalThis.window) {
  if (windowImpl.Razorpay) return Promise.resolve(windowImpl.Razorpay);
  if (!scriptPromise) scriptPromise = new Promise((resolve, reject) => {
    const script = documentImpl.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.onload = () => windowImpl.Razorpay ? resolve(windowImpl.Razorpay) : reject(new Error("Checkout unavailable"));
    script.onerror = () => reject(new Error("Checkout failed to load"));
    documentImpl.head.appendChild(script);
  }).catch(error => { scriptPromise = null; throw error; });
  return scriptPromise;
}

export async function checkout({client, product, requestId, name, RazorpayClass, billingPath = "/billing"}) {
  const order = await client.request(billingPath + "/checkout", {method: "POST", body: {product, request_id: requestId}});
  if (order.state === "paid") throw new Error("Order already paid; refresh its receipt");
  const Gateway = RazorpayClass || await loadRazorpay();
  return new Promise((resolve, reject) => {
    const instance = new Gateway({...order, name,
      handler: async result => {
        try {
          resolve(await client.request(billingPath + "/confirm", {method: "POST", body: {
            order_id: order.order_id, payment_id: result.razorpay_payment_id, signature: result.razorpay_signature,
          }}));
        } catch (error) { reject(error); }
      },
      modal: {ondismiss: () => reject(new Error("Checkout dismissed; payment status may need refresh"))},
    });
    instance.on("payment.failed", () => reject(new Error("Payment failed; refresh status before another attempt")));
    instance.open();
  });
}

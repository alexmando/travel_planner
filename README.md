# Travel Planner

## Project Setup

Inside the `travel_planner` folder, create a file named `.env`.

The `.env` file must contain the following information:

```env
RAPIDAPI_KEY=
RAPIDAPI_HOST_KIWI=kiwi-com-cheap-flights.p.rapidapi.com
RAPIDAPI_HOST_BOOKING=booking-com.p.rapidapi.com
GROQ_API_KEY=
MODEL=groq/meta-llama/llama-4-scout-17b-16e-instruct
```

## API Keys

### Groq

The Groq API key can be created for free from the official website:

https://groq.com/

After creating an account, generate an API key and paste it into:

```env
GROQ_API_KEY=
```

---

### Kiwi API (for flights)

The Kiwi API is available through RapidAPI:

https://rapidapi.com/emir12/api/kiwi-com-cheap-flights/playground/apiendpoint_2712d869-a313-45eb-8c86-49b36b2cdf34

After subscribing to the API, copy your RapidAPI key and paste it into:

---

### Booking API (for hotel and activities)

The Booking API is available through RapidAPI:

https://rapidapi.com/tipsters/api/booking-com/playground/apiendpoint_5d30cd33-238b-447a-9696-70faf39f7eb0

---

## Note

No credit card is required to use the available free plans for these APIs.

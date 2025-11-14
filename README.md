# Singhacks Travel Insurance Chatbot
### Motivation

This project was developed for the 2025 Singhacks Hackathon. Our goal was to build an intelligent travel insurance chatbot that can analyse past claims data to identify potential risks for a user’s upcoming trip. For example, when a user says, “I’m going to Okinawa, Japan in July 2026—what risks should I expect and what insurance should I buy?”, the chatbot returns a list of likely risks and recommends an appropriate insurance plan based on historical patterns.

### Methodology

We extracted 20,000 travel insurance claims from a PostgreSQL database and performed data cleaning, standardisation, outlier clipping, and activity categorisation. Each claim was labelled as Low, Medium, or High risk based on severity thresholds. Categorical features were encoded and fed into a hybrid machine-learning model combining Random Forest and XGBoost, with a Logistic Regression meta-model to produce final risk classifications. The chatbot then uses these predictions—together with user inputs such as destination, activity, and claim type—to recommend tailored insurance plans (Basic, Silver, Gold, or Platinum).

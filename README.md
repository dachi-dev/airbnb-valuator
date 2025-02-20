### scraper.py
This module is  responsible for scraping Airbnb. It uses selenium to navigate to a list of cities, scrape the listings, and pushes raw metrics to a database to later be used in the data fusion engine.

To run it, install the python dependencies and run `python scraper.py`, by default it uses the geckodriver (Firefox), so you should see that browser open up unless you have it in headless mode (recommended for prod).

### airbnb_regression_model.py
The machine learning (ML) model is used to predict property values for Airbnb listings based on their rental characteristics. Since we can't scrape every listing, the model allows us to generalize property values from a small sample to the entire Airbnb platform.

The model learns how Airbnb features correlate with property values.
It finds patterns like:

        Higher nightly prices → Higher home values.
        More bedrooms → More expensive properties.
        Urban areas → More valuable homes.


After training, we apply the model to Airbnb listings we didn’t scrape. It estimates missing property values based on their features. We then scale to estimate Airbnb’s total property value

    Compute the average predicted property value.
    Multiply by the total estimated number of Airbnb listings.

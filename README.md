# San Antonio Spurs Interactive Dashboard

This project is an interactive dashboard I built to track and visualize data for the San Antonio Spurs. It's a personal project I created to sharpen my skills in data engineering, from pulling data from an API to presenting it in a user-friendly way.

## My Learning Journey

I built this dashboard to get hands-on experience with key data engineering tasks. My main goals for this project were:

-   **Working with APIs:** Practice fetching live stats from the `nba-api`.
-   **Processing Data:** Use Python and pandas to clean up the raw API data and get it ready for analysis.
-   **Visualizing Data:** Create an interactive UI with Streamlit and Plotly to make the data easy to explore.
-   **Applying Good Practices:** Focus on writing clean, maintainable code.

## Tech Stack

-   **Python:** For all the data fetching and processing logic.
-   **Streamlit:** To build the web app interface.
-   **Pandas:** For data wrangling.
-   **Plotly:** For creating the interactive charts.
-   **nba-api:** The library used to connect to the NBA stats API.

## Data Engineering Best Practices

I focused on writing clean and efficient code, following some key data engineering practices:

-   **Dependency Management:** The `requirements.txt` file lists all the necessary packages, which makes it simple to get the project running.
-   **Modular Code:** I broke the code into smaller functions for specific tasks like fetching or visualizing data.
-   **Caching:** To make the app faster and avoid hitting the API too often, I used Streamlit's caching (`@st.cache_data`) to save data after the first fetch.
-   **Code Readability:** I added comments to explain what different parts of the code do.
-   **Documentation:** This README file serves as the main documentation for the project.

## How to Run It

1.  **Get the code:** Clone the repository or download the files.

2.  **Set up your environment:**
    ```bash
    # It's a good idea to use a virtual environment
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install what you need:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the Streamlit app:**
    ```bash
    streamlit run SpursAnalysis.py
    ```

5.  **Open your web browser** and navigate to the local URL provided by Streamlit (usually `http://localhost:8501`).

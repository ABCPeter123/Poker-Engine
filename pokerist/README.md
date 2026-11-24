# Pokerist screenshot review (experimental)

This optional local tool reads a saved screenshot after a hand. It is separate from the live table tracker and does not connect to Pokerist or feed advice into a game. Use only for review or other permitted analysis.

From the repository directory on Windows:

    py -m pip install -r pokerist/requirements.txt
    py pokerist/review.py

Choose a saved landscape screenshot. The script prints unverified candidates and saves pokerist-review.json. You can also specify the screenshot as an argument.

    py pokerist/review.py "C:\\path\\to\\screenshot.jpg"

Optional number OCR requires a separately installed Tesseract executable. If not on PATH:

    py pokerist/review.py "C:\\path\\to\\screenshot.jpg" --tesseract "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

The 1536x709 five-seat layout and rank glyphs J, 4, 9, Q and 3 were calibrated from the supplied screenshot. Other ranks, alternate layouts, bet fields, dealer and active-player tracking are not yet calibrated. A template match is a candidate, not a validated reading; all values should be reviewed. No screenshots are stored in the repository or sent anywhere. No real-time screen capture, automatic actions or live recommendations.

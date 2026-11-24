# Pokerist screenshot review (experimental)

This optional local tool reads a saved screenshot after a hand. It is separate from the live table tracker and does not connect to Pokerist or feed advice into a game. Use only for review or other permitted analysis.

From the repository directory on Windows:

    py pokerist/review.py

Each launch automatically runs pip install against the complete requirements.txt using the same Python interpreter. Already satisfied requirements are reused; missing dependencies are installed. If installation fails, the program stops before importing Pillow or NumPy. Tesseract is an optional external executable and is not installed by pip.

Choose a saved landscape screenshot. The script prints unverified candidates and saves pokerist-review.json. You can also specify the screenshot as an argument.

    py pokerist/review.py "C:\\path\\to\\screenshot.jpg"

Optional number OCR requires a separately installed Tesseract executable. If not on PATH:

    py pokerist/review.py "C:\\path\\to\\screenshot.jpg" --tesseract "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

The 1536x709 five-seat layout and rank glyphs J, 4, 9, Q and 3 were calibrated from the supplied screenshot. Other ranks, alternate layouts, bet fields, dealer and active-player tracking are not yet calibrated. A template match is a candidate, not a validated reading; all values should be reviewed. No screenshots are stored in the repository or sent anywhere. No real-time screen capture, automatic actions or live recommendations.

## Profile indicators and seat changes

The optional review output now includes experimental seat evidence. A bright green segment plus red or amber in a profile-base crop produces a multicolor-band candidate. One unique candidate is reported separately from the unverified active-player field. Multiple candidates are marked as conflicting. A saved previous screenshot can be used to measure brightness and appearance changes:

    py pokerist/review.py later.jpg --previous earlier.jpg

Darkened avatars can correspond to nonactive, folded, or obscured players. A large appearance change may be a departure or animation; neither is promoted to a fold or departure automatically. Yellow/orange regions near approximate bet locations are searched for the literal ALL IN label using optional Tesseract. Color alone never implies all-in. Absence of OCR text remains unknown. These cues require positive screenshots for calibration; they do not drive the table tracker or live recommendations.

Run synthetic cue tests:

    py -m unittest discover -s pokerist -p "test_*.py"

# PMP Quiz App

Desktop PMP practice quiz app (Tkinter) with JSON-based question banks, instant explanations, and configurable question-set loading.

## Requirements

- Python 3.11+

## Run Locally

```powershell
cd "PMP Test"
python .\quiz_app.py
```

## Build EXE (Optional)

```powershell
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed --name PMPQuiz quiz_app.py
```

The executable is created in `dist/PMPQuiz.exe`.

## Load Practice Questions

1. Put `.json` question files in the `questions/` folder (recommended), or keep them anywhere on your machine.
2. Start the app.
3. In the file picker:
   - Select files shown from the default folder, or
   - Click `Browse Folder` to load a folder of JSON files, or
   - Click `Browse Files` to pick specific JSON files.
4. Click `Start Quiz`.
5. (Optional) Turn on `Show Explanation After Answer` during the quiz.

## JSON Format

```json
{
  "questions": [
    {
      "qid": "Q-1",
      "stem": "Question text",
      "choices": ["A", "B", "C", "D"],
      "correct_index": 1,
      "explanation": "Why B is correct"
    }
  ]
}
```

## Project Layout

- `quiz_app.py`: main application.
- `questions/`: quiz question sets in JSON format.
- `.gitignore`: excludes local build artifacts (`dist/`, `build/`, `*.exe`, etc.).

# PMP Quiz App

Desktop PMP practice quiz app (Tkinter) with JSON-based question banks, instant explanations, and configurable question-set loading.

## Download (Windows PowerShell)

```powershell
git clone https://github.com/aaronj1605/pmp-quiz-app.git
cd .\pmp-quiz-app
```

## Run (Windows PowerShell)

```powershell
python .\quiz_app.py
```

## Build EXE (Windows PowerShell, Optional)

```powershell
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed --name PMPQuiz quiz_app.py
```

The executable is created in `dist/PMPQuiz.exe`.

## Load Practice Questions

1. Start the app.
2. Select question files from `questions\`, or use `Browse Folder`/`Browse Files`.
3. Click `Start Quiz`.

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

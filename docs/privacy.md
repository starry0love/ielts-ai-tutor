# Privacy

IELTS AI Tutor is designed as a local-first desktop app.

- User learning records are stored in a local SQLite database.
- API keys are stored on the user's machine.
- The open-source version does not include any built-in API key.
- The app does not include a cloud account system.
- When AI features are used, the user's configured model provider receives the relevant prompt, essay, review, or learning profile content.

Do not commit local `.env` files, SQLite databases, exported learning records, or packaged app data to Git.

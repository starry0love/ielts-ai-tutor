# Privacy

IELTS AI Tutor is designed as a local-first desktop app.

- User learning records are stored in a local SQLite database.
- API keys are stored in plain text in the user's local `.env` configuration file.
- The open-source version does not include any built-in API key.
- The app does not include a cloud account system.
- When AI features are used, the user's configured model provider receives the relevant prompt, essay, review, or learning profile content.

Do not commit or share local `.env` files, SQLite databases, exported learning records, screenshots that reveal API keys, or packaged app data. A future version may move API key storage to an OS credential store such as Windows Credential Manager.

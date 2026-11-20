# ✉️ Email Agent

An AI email assistant built with **LangGraph** and **LangChain**. Describe the email you want in plain language (English or Roman Urdu), review the draft, and the agent sends it for you after your approval.

## What It Does

**The problem it solves:** Writing professional emails takes time, and sending a wrong or badly worded email can be embarrassing. Business owners often just want to say *"Tell John the meeting is at 5 PM"* and have a polished email ready, without opening their mail app.

**How it helps:** The user types the request in simple language. The agent:
1. Extracts the recipient's name, email address and the reason for the email.
2. Drafts a clear subject line and a polite, professional email body.
3. Pauses and shows the draft (human-in-the-loop). Reply `Yes` to approve, or type what to change and it rewrites the draft (up to 5 revisions).
4. Sends the email over SMTP only after approval.

Nothing is ever sent without your confirmation.

## Flow

```
START → retriever → has recipient email? ─ no → no_email → END
                          │
                         yes
                          ↓
                        draft → review ─ approved → send → END
                          ↑        │
                          └─ feedback ─┘
                                   └─ limit reached → cancel → END
```

## Memory

Conversation state is saved with a LangGraph checkpointer (SQLite) per `thread_id`. The approval step uses it to pause and resume the graph.

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file:

```env
DEEPSEEK_API_KEY=your_deepseek_key
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_FROM=your_email@gmail.com
SMTP_PASS=your_app_password
```

For Gmail, use an **App Password**, not your normal password. The code uses `SMTP_SSL`, so the port is usually `465`.

## Usage

```bash
python main.py
```

Example: *"Email john@example.com that tomorrow's meeting is at 5 PM"*

The agent shows the draft, then asks:

```
Type 'Yes' to approve or write what to change:
```


## Safety Notes

- The agent sends **real emails**. Always review the draft before approving, and use your own address while testing.
- The recipient's email address must be written in your message. The agent does not look it up anywhere.
- Never commit your `.env` file or SMTP password to Git.
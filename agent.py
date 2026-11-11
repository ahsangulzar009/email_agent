from dotenv import load_dotenv

load_dotenv()

from langchain_deepseek import ChatDeepSeek
from langgraph.graph import StateGraph, END, START

# from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command, interrupt
from pydantic import BaseModel, Field
from typing import Annotated, Literal
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from send_email import send_email

llm = ChatDeepSeek(model="deepseek-flash", temperature=0.6, extra_body={"thinking": {"type": "disabled"}},)


class EmailState(BaseModel):
    question: str = ""
    mail_reason: str = ""
    recipient_name: str = ""
    recipient_email: str = ""
    subject: str = ""
    body: str = ""
    feedback: str = ""
    feedback_count: int = 0
    response: str = ""

    ### Retriever Node


class UserDetails(BaseModel):
    mail_reason: str = Field(
        description="Reason of the email, like why user want to send this email"
    )
    recipient_name: str = Field(
        description="recipient / reciever name, if available else ''"
    )
    recipient_email: str = Field(description="recipient / reciever email address")


def retriever_node(state: EmailState):
    llm_for_user_details = llm.with_structured_output(UserDetails)
    userDetails: UserDetails = llm_for_user_details.invoke(
        f"Retrieve the user details from this query: {state.question}"
    )

    return {
        "mail_reason": userDetails.mail_reason,
        "recipient_name": userDetails.recipient_name,
        "recipient_email": userDetails.recipient_email,
    }


### Draft Node
class DraftEmail(BaseModel):
    subject: str = Field(
        description=(
            "A clear, concise email subject line that summarizes the purpose of the email. "
            "Maximum 10 words (under 60 characters). Do not use quotes, emojis, or ALL CAPS."
        )
    )
    body: str = Field(
        description=(
            "The complete email body in a professional and polite tone. "
            "Start with a greeting using the recipient's name (use 'Hello,' if the name is unknown). "
            "Clearly explain the reason for the email, include all relevant details given by the user, "
            "and state any request or next step. "
            "End with a courteous closing such as 'Best regards,' followed by the sender's name if available. "
            "Do not include the subject line inside the body. "
            "Do not invent facts, dates, or details that the user did not provide."
        )
    )

def draft_node(state: EmailState):
    """Draft Email"""
    draft_email = llm.with_structured_output(DraftEmail)

    prompt = (
        f"Write an email to {state.recipient_name or 'the recipient'} "
        f"about: {state.mail_reason}. "
        "Keep the body under 200 words."
    )

    if state.feedback:
        prompt += (
        f"\n\nPrevious draft:\nSubject: {state.subject}\nBody: {state.body}\n\n"
        f"Rewrite it considering this feedback: {state.feedback}"
    )

    draftEmail: DraftEmail = draft_email.invoke(prompt)

    return {"subject": draftEmail.subject, "body": draftEmail.body}


### Review Node
def review_node(state: EmailState):
    response = interrupt({"message": "Type 'Yes' to Approve or write what to change."})

    if response.strip().lower() in ("yes", "y", "ok"):
        return {"feedback": ""}

    return {"feedback": response, "feedback_count": state.feedback_count + 1}


def router(state: EmailState) -> Literal["draft", "send", "cancel"]:
    if not state.feedback or state.feedback == "":
        return "send"
    if state.feedback_count > 50:
        return "cancel"
    return "draft"


def cancel_node(state: EmailState):
    return {
        "response": "Email not send, Because you have reached the limit of feedbacks. "
    }


def sendEmail_node(state: EmailState):
    """Send final email"""
    res = send_email(state.recipient_email, state.subject, state.body)

    return {"response": res}


graph = StateGraph(EmailState)

graph.add_node("retriever", retriever_node)
graph.add_node("draft", draft_node)
graph.add_node("review", review_node)
graph.add_node("send", sendEmail_node)
graph.add_node("cancel", cancel_node)

graph.add_edge(START, "retriever")
graph.add_edge("retriever", "draft")
graph.add_edge("draft", "review")
graph.add_conditional_edges("review", router)
graph.add_edge("send", END)
graph.add_edge("cancel", END)

connection = sqlite3.connect("email.sqlite3", check_same_thread=False)
sql_memory = SqliteSaver(connection)
sql_memory.setup()

app = graph.compile(checkpointer=sql_memory)


while True:
    query = input("Enter your email request (or 'exit' to quit): ")
    if query.strip().lower() in ("exit", "quit"):
        break

    config = {"configurable": {"thread_id": "1"}}
    res = app.invoke({"question": query}, config=config)

    while True:
        state = app.get_state(config)

        if not state.next:
            break

        print("\n", "-" * 60)
        print("Subject: ", res["subject"])
        print("Body: ", res["body"])
        print("\n", "-" * 60)

        feedback = input("Type 'Yes' to Approve or write what to change: ")
        res = app.invoke(Command(resume=feedback), config=config)

    print("AI: ", res["response"])

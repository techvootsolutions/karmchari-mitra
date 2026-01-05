import os
from omnidimension import Client
from config import Config

def setup_agent():
    api_key = Config.OMNIDIMENSION_API_KEY
    if not api_key:
        print("Error: OMNIDIMENSION_API_KEY not found in environment variables.")
        print("Please set it in your .env file.")
        return

    # Initialize client
    print("Initializing Omnidimension Client...")
    try:
        client = Client(api_key)
    except Exception as e:
        print(f"Failed to initialize client: {e}")
        return

    try:
        # Create an agent
        response = client.agent.create(
            name="Resume Follow-Up Agent",
            welcome_message="""Hi [user_name], this is [Techvootbot] from [Techvoot Solution] calling to follow up on your resume submission for the [job Title] developer position.""",
            context_breakdown=[
                        {"title": "Agent Role & Context (MANDATORY for Outbound agents)", "body": """ You are a representative from [company_name] calling individuals who submitted a form expressing interest in the [position]. Your goal is to collect additional information from these individuals to complete their application. You are contacting recent form submitters (users) who are interested in pursuing a job at your company. """ , 
                        "is_enabled" : True},
                        {"title": "Introduction", "body": """ Introduce yourself by name and clarify your role: 'Hi [user_name], this is [agent_name] from [company_name]. I hope I'm not catching you at a bad time.' Then state your purpose: 'I'm reaching out to follow up on the resume you submitted for the WordPress developer position.' Wait for confirmation that it's a good time to talk. """ , 
                        "is_enabled" : True},
                        {"title": "Purpose Statement", "body": """ Explain the purpose clearly: 'We need to gather a few more pieces of information to complete your application. This will help us move forward in the recruitment process.' Ensure the user is comfortable with this call and confirm their willingness to proceed with the questions. """ , 
                        "is_enabled" : True},
                        {"title": "Information Gathering", "body": """ Politely and clearly ask each of the following questions, allowing time for the user to answer each one:\n- 'Could you please give us a brief introduction about yourself?'\n- 'May I know your current position?'\n- 'What is your current salary?'\n- 'What would be your expected salary for this role?'\n- 'What is your notice period with your current employer?' Acknowledge each response: 'Thank you for sharing that information.' """ , 
                        "is_enabled" : True},
                        {"title": "Conclusion and Closing", "body": """ Thank the user for their time and provide closure: 'Thank you for providing these details. This information helps us proceed with your application process. If we need any more information, we'll be in touch. Have a fantastic day!' """ , 
                        "is_enabled" : True}
            ],
            call_type="Outgoing",
            transcriber={
                "provider": "Azure",
                "silence_timeout_ms": 400
            },
            model={
                "model": "gpt-4.1-mini",
                "temperature": 0.7
            },
            voice={
                "provider": "sarvam",
                "voice_id": "anushka"
            },
        )

        print("\nAgent Created Successfully!")
        print(response)
        
        # Optionally save the agent ID to a file or database if needed
        if hasattr(response, 'id'):
             print(f"Agent ID: {response.id}")

    except Exception as e:
        print(f"\nError creating agent: {e}")

if __name__ == "__main__":
    setup_agent()

import logging
import asyncio
from fastapi_mail import FastMail, MessageSchema
from mail_config import conf
from jinja2 import Template
from typing import Dict, List
import os
from database import get_db_connection, execute_query  # Fixed import
from datetime import datetime
import pytz

EMAIL_SENDER = conf.MAIL_FROM

def send_plain_mail(subject: str, message: str, from_: str, to: List[str]):
    """Send plain text email"""
    try:
        # Filter valid emails
        valid_emails = [email for email in to if email and not email.startswith("noemail")]
        
        if not valid_emails:
            logging.info("All emails were skipped - no valid recipients.")
            return True

        # Create email message
        email = MessageSchema(
            subject=subject,
            recipients=valid_emails,  # This should be a list, not a string
            body=message,
            subtype="plain"
        )

        # Send email using FastMail
        fm = FastMail(conf)
        
        # Use asyncio to run the async send_message method
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(fm.send_message(email))
        loop.close()
        
        logging.info(f"Email sent successfully to: {', '.join(valid_emails)}")
        return True
        
    except Exception as e:
        logging.exception(f"Error in send_plain_mail: {repr(e)}")
        return False


def send_passenger_complain_email(complain_details: Dict):
    """Send complaint email to war room users"""
    war_room_user_in_depot = []
    s2_admin_users = []
    railway_admin_users = []
    assigned_users_list = []
    
    all_users_to_mail = []
    
    s2_admin_users = []
    railway_admin_users = []
    assigned_users_list = []
    
    all_users_to_mail = []
    
    train_depo = complain_details.get('train_depot', '')
    train_no = str(complain_details.get('train_no', '')).strip()
    complaint_date = complain_details.get('created_at', '') 
    journey_start_date = complain_details.get('date_of_journey', '')

    ist = pytz.timezone('Asia/Kolkata')
    complaint_created_at = datetime.now(ist).strftime("%d %b %Y, %H:%M")

    
    try:
        # Query to get war room users
        query = """
            SELECT u.* 
            FROM user_onboarding_user u 
            JOIN user_onboarding_roles ut ON u.user_type_id = ut.id 
            WHERE ut.name = 'war room user'
        """
        
        conn = get_db_connection()
        war_room_users = execute_query(conn, query)
        conn.close()

        if war_room_users:
            for user in war_room_users:
                # Check if user's depot matches train depot
                user_depo = user.get('depo', '')
                if user_depo and train_depo and train_depo in user_depo:
                    war_room_user_in_depot.append(user)
        else:
            logging.info(f"No war room users found for depot {train_depo} in complaint {complain_details['complain_id']}")
            
        s2_admin_query = """
            SELECT u.* 
            FROM user_onboarding_user u 
            JOIN user_onboarding_roles ut ON u.user_type_id = ut.id 
            WHERE ut.name = 's2 admin'
        """
        conn = get_db_connection()
        s2_admin_users = execute_query(conn, s2_admin_query)
        
        railway_admin_query = """
            SELECT u.* 
            FROM user_onboarding_user u 
            JOIN user_onboarding_roles ut ON u.user_type_id = ut.id 
            WHERE ut.name = 'railway admin'
        """
        railway_admin_users = execute_query(conn, railway_admin_query)
        
        # Updated query to get train access users with better filtering
        assigned_users_query = """
            SELECT u.email, u.id, u.first_name, u.last_name, ta.train_details
            FROM user_onboarding_user u
            JOIN trains_trainaccess ta ON ta.user_id = u.id
            WHERE ta.train_details IS NOT NULL 
            AND ta.train_details != '{}'
            AND ta.train_details != 'null'
        """
        conn = get_db_connection()
        assigned_users_raw = execute_query(conn, assigned_users_query)
        conn.close()
        
        # Get train number and complaint date for filtering
        train_no = str(complain_details.get('train_number', '')).strip()
        
        # Handle created_at whether it's a string or datetime object
        created_at_raw = complain_details.get('created_at', '')
        try:
            if isinstance(created_at_raw, datetime):
                complaint_date = created_at_raw.date()
            elif isinstance(created_at_raw, str):
                if len(created_at_raw) >= 10:
                    complaint_date = datetime.strptime(created_at_raw, "%Y-%m-%d").date()
                else:
                    complaint_date = None
            else:
                complaint_date = None
        except (ValueError, TypeError):
            complaint_date = None
            

        if complaint_date and train_no:
            for user in assigned_users_raw:
                try:
                    train_details_str = user.get('train_details', '{}')
                    
                    # Handle case where train_details might be a string or already parsed
                    if isinstance(train_details_str, str):
                        train_details = json.loads(train_details_str)
                    else:
                        train_details = train_details_str
                    
                    # Check if the train number exists in train_details
                    if train_no in train_details:
                        for access in train_details[train_no]:
                            try:
                                origin_date = datetime.strptime(access.get('origin_date', ''), "%Y-%m-%d").date()
                                end_date_str = access.get('end_date', '')
                                
                                # Check if complaint date falls within the valid range
                                if end_date_str == 'ongoing':
                                    is_valid = complaint_date >= origin_date
                                else:
                                    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                                    is_valid = origin_date <= complaint_date <= end_date
                                
                                if is_valid:
                                    assigned_users_list.append(user)
                                    break  # Only need one match per user
                                    
                            except (ValueError, TypeError) as date_error:
                                logging.warning(f"Date parsing error for user {user.get('id')}: {date_error}")
                                continue
                                
                except (json.JSONDecodeError, TypeError) as json_error:
                    logging.warning(f"JSON parsing error for user {user.get('id')}: {json_error}")
                    continue

        # all_users_to_mail = [{"email": "writetohm19@gmail.com"}]
        all_users_to_mail = war_room_user_in_depot + s2_admin_users + railway_admin_users + assigned_users_list
     
    except Exception as e:
        logging.error(f"Error fetching users: {e}")
        logging.error(f"Error fetching users: {e}")

    try:
        # Prepare email content
        subject = f"Complaint received for train number: {complain_details['train_no']}"
        pnr_value = complain_details.get('pnr', 'PNR not provided by passenger')

        
        context = {
            "user_phone_number": complain_details.get('user_phone_number', ''),
            "passenger_name": complain_details.get('passenger_name', ''),
            "train_no": complain_details.get('train_no', ''),
            "train_name": complain_details.get('train_name', ''),
            "pnr": pnr_value,
            "berth": complain_details.get('berth', ''),
            "coach": complain_details.get('coach', ''),
            "complain_id": complain_details.get('complain_id', ''),
            "created_at": complaint_created_at,
            "description": complain_details.get('description', ''),
            "train_depo": complain_details.get('train_depo', ''),
            "complaint_date": complaint_date,
            "start_date_of_journey": journey_start_date,
            'site_name': 'RailSathi',
        }

        # Load and render template
        template_path = os.path.join("templates", "complaint_creation_email_template.txt")
        
        if not os.path.exists(template_path):
            # Fallback to inline template if file doesn't exist
            template_content = """
                Passenger Complaint Submitted

                A new passenger complaint has been received.

                Complaint ID   : {{ complain_id }}
                Submitted At  : {{ created_at }}

                Passenger Info:
                ---------------
                Name           : {{ passenger_name }}
                Phone Number   : {{ user_phone_number }}

                Travel Details:
                ---------------
                Train Number   : {{ train_no }}
                Train Name     : {{ train_name }}
                Coach          : {{ coach }}
                Berth Number   : {{ berth }}
                PNR            : {{ pnr }}

                Complaint Details:
                ------------------
                Description    : {{ description }}

                Train Depot    : {{ train_depo }}
                
                Please take necessary action at the earliest.

                This is an automated notification. Please do not reply to this email.

                Regards,  
                Team RailSathi
            """
        else:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
        
        template = Template(template_content)
        message = template.render(context)

        # Create list of unique email addresses for logging
        assigned_user_emails = [user.get('email') for user in assigned_users_list if user.get('email')]
        assigned_user_emails = list(dict.fromkeys(assigned_user_emails))  # Remove duplicates
        
        if assigned_user_emails:
            logging.info(f"Train access users to be notified: {', '.join(assigned_user_emails)}")

        # Send emails to war room users, s2 admins, railway admins, and train access users
        # Create list of unique email addresses for logging
        assigned_user_emails = [user.get('email') for user in assigned_users_list if user.get('email')]
        assigned_user_emails = list(dict.fromkeys(assigned_user_emails))  # Remove duplicates
        
        if assigned_user_emails:
            logging.info(f"Train access users to be notified: {', '.join(assigned_user_emails)}")

        # Send emails to war room users, s2 admins, railway admins, and train access users
        emails_sent = 0
        for user in all_users_to_mail:
            email = user.get('email', '')
        for user in all_users_to_mail:
            email = user.get('email', '')
            if email and not email.startswith("noemail") and '@' in email:
                try:
                    success = send_plain_mail(subject, message, EMAIL_SENDER, [email])
                    if success:
                        emails_sent += 1
                        logging.info(f"Email sent to {email} for complaint {complain_details['complain_id']}")
                    else:
                        logging.error(f"Failed to send email to {email}")
                except Exception as e:
                    logging.error(f"Error sending email to {email}: {e}")

        if not all_users_to_mail:
            logging.info(f"No users found for depot {train_depo} and train {train_no} in complaint {complain_details['complain_id']}")
            return {"status": "success", "message": "No users found for this depot and train"}
        if not all_users_to_mail:
            logging.info(f"No users found for depot {train_depo} and train {train_no} in complaint {complain_details['complain_id']}")
            return {"status": "success", "message": "No users found for this depot and train"}
        
        return {"status": "success", "message": f"Emails sent to {emails_sent} users"}
        return {"status": "success", "message": f"Emails sent to {emails_sent} users"}
        
    except Exception as e:
        logging.error(f"Error in send_passenger_complain_email: {e}")
        return {"status": "error", "message": str(e)}
    
    
def execute_sql_query(sql_query: str):
    """Execute a SELECT query safely"""
    if not sql_query.strip().lower().startswith("select"):
        raise ValueError("Only SELECT queries are allowed")

    conn = get_db_connection()
    try:
        results = execute_query(conn, sql_query)
        return results
    finally:
        conn.close()

"""
Hardcoded event/session/step content for the MAPS Physiotherapy Leadership
Summit 2083 facilitator worksheet. This is intentionally NOT a generic
question-builder -- it mirrors the exact worksheet PDF for this one event.

Each session is a list of "steps". Each step has one or more "sections".
Section `type` drives both how summit_app/views.py parses the POSTed data
and which partial template renders it (see templates/summit/session_step.html).

Section types used below:
- checklist_other : checkboxes (+ an automatic "Other" checkbox/text field)
- score_for_prior  : renders a 1-5 score input for each item chosen in an
                     earlier step's checklist_other section
- top_n_select     : renders checkboxes (capped at n) over an earlier step's
                     checklist_other selections, for picking the "Top 3"
- free_text        : a single textarea
- text_fields      : several independently labeled textareas
- number_fields     : several independently labeled short text/number inputs
- radio            : single-choice radio buttons
- text             : a single-line text input
"""

EVENT_TITLE = "MAPS Physiotherapy Leadership Summit 2083"
EVENT_SUBTITLE = "Facilitator Table Discussion — Data Collection"

TABLE_NUMBERS = [1, 2, 3, 4, 5, 6]

SESSION_ORDER = ["session1", "session2", "session3"]

SESSIONS = {
    "session1": {
        "title": "न्यूनतम फिजियोथेरापी सेवा मापदण्ड (Minimum Standards of Physiotherapy Practice)",
        "short_title": "Session 1: Minimum Standards",
        "steps": [
            {
                "key": "step1",
                "title": "Root Cause Identification (समस्या पहिचान)",
                "intro": "मध्यपुरका अधिकांश क्लिनिकहरूमा गुणस्तरीय फिजियोथेरापी सेवा प्रदान गर्न सबैभन्दा ठूलो चुनौती के हो?",
                "sections": [
                    {
                        "type": "checklist_other",
                        "name": "causes",
                        "label": "Key Issues Identified",
                        "options": [
                            ("assessment", "Assessment"),
                            ("documentation", "Documentation"),
                            ("exercise_treatment", "Exercise-Based Treatment"),
                            ("patient_education", "Patient Education"),
                            ("followup_system", "Follow-up System"),
                            ("professional_identification", "Professional Identification"),
                            ("ethical_practice", "Ethical Practice"),
                            ("referral_system", "Referral System"),
                            ("infection_control", "Infection Control"),
                        ],
                    },
                ],
            },
            {
                "key": "step2",
                "title": "Impact Rating (प्रभाव मूल्याङ्कन)",
                "intro": "प्रत्येक कारणले गुणस्तरीय तथा एकरूप फिजियोथेरापी सेवा प्रदान गर्न कति प्रभाव पारिरहेको छ भन्ने आधारमा १ देखि ५ सम्म अंक दिनुहोस्, अनि सबैभन्दा बढी प्रभाव पार्ने शीर्ष तीन कारणमा सहमति गर्नुहोस्।",
                "sections": [
                    {
                        "type": "score_for_prior",
                        "name": "impact_scores",
                        "label": "Impact Score (1 = Very Low ... 5 = Very High)",
                        "source_step": "step1",
                        "source_field": "causes",
                    },
                    {
                        "type": "top_n_select",
                        "name": "top3",
                        "label": "Top 3 सबैभन्दा बढी प्रभाव पार्ने कारणहरू",
                        "source_step": "step1",
                        "source_field": "causes",
                        "n": 3,
                    },
                ],
            },
            {
                "key": "step3",
                "title": "Possible Solutions (सम्भावित समाधान)",
                "intro": "प्रत्येक फिजियोथेरापी क्लिनिकले अनिवार्य रूपमा पालना गर्नुपर्ने न्यूनतम सेवा मापदण्डहरू के-के हुनुपर्छ?",
                "sections": [
                    {
                        "type": "checklist_other",
                        "name": "solution_checks",
                        "label": "सुझावहरू",
                        "options": [
                            ("initial_assessment", "प्रत्येक बिरामीको प्रारम्भिक Assessment अनिवार्य"),
                            ("documentation", "Documentation अनिवार्य"),
                            ("goal_setting", "Goal Setting हुनुपर्छ"),
                            ("exercise_prescription", "Exercise Prescription सबै बिरामीका लागि आवश्यक"),
                            ("patient_education", "Patient Education अनिवार्य"),
                            ("referral", "Referral गर्नुपर्ने अवस्था स्पष्ट"),
                            ("name_tag", "Professional Name Tag तथा Registration Number देखिनुपर्ने"),
                            ("infection_control", "Infection Control का आधारभूत मापदण्ड"),
                        ],
                    },
                    {
                        "type": "free_text",
                        "name": "solutions_free_text",
                        "label": "समूहबाट आएका अन्य सम्भावित समाधानहरू",
                        "rows": 4,
                    },
                ],
            },
            {
                "key": "step4",
                "title": "Minimum Standards Framework",
                "intro": "हरेक क्लिनिकले अनिवार्य रूपमा पालना गर्नुपर्ने न्यूनतम सेवा मापदण्डहरू (Minimum Standards) के-के हुनुपर्छ?",
                "sections": [
                    {
                        "type": "checklist_other",
                        "name": "framework_items",
                        "label": "न्यूनतम सेवा मापदण्डहरू (Group Consensus)",
                        "options": [
                            ("comprehensive_assessment", "प्रत्येक बिरामीका लागि Comprehensive Assessment अनिवार्य गर्ने"),
                            ("documentation", "Assessment तथा Treatment Documentation अनिवार्य गर्ने"),
                            ("evidence_based_exercise", "Evidence-Based Exercise Therapy लाई उपचारको मुख्य आधार बनाउने"),
                            ("patient_education", "Condition-specific Patient Education प्रदान गर्ने"),
                            ("followup_outcome", "Follow-up तथा Outcome Monitoring प्रणाली विकास गर्ने"),
                            ("professional_identification", "Professional Identification तथा Scope of Practice स्पष्ट रूपमा कार्यान्वयन गर्ने"),
                            ("referral_communication", "आवश्यक अवस्थामा Referral तथा Inter-professional Communication गर्ने"),
                            ("ethics_infection", "Ethical Practice तथा Infection Prevention Standards पालना गर्ने"),
                            ("maps_guideline", "MAPS द्वारा Minimum Practice Standards Guideline विकास गर्ने"),
                        ],
                    },
                    {
                        "type": "text_fields",
                        "name": "standard_texts",
                        "label": "Standard विवरण (आवश्यक भएमा मात्र भर्नुहोस्)",
                        "fields": [
                            ("assessment_standard", "Assessment Standard"),
                            ("documentation_standard", "Documentation Standard"),
                            ("treatment_standard", "Treatment Standard"),
                            ("patient_education_standard", "Patient Education Standard"),
                            ("followup_outcome_standard", "Follow-up & Outcome Monitoring"),
                            ("professional_ethics_standard", "Professional Ethics & Scope of Practice"),
                            ("referral_standard", "Referral & Communication"),
                            ("other_standard", "Other Recommended Standards"),
                        ],
                    },
                ],
            },
            {
                "key": "step5",
                "title": "Final Recommendation Summary",
                "intro": "आजको छलफलबाट आएका मुख्य निष्कर्षहरूलाई एकीकृत गरी समूहको अन्तिम सिफारिस लेख्नुहोस्।",
                "sections": [
                    {"type": "free_text", "name": "key_solutions", "label": "Key Solutions", "rows": 4},
                    {"type": "free_text", "name": "recommended_framework", "label": "Recommended Minimum Standards Framework", "rows": 4},
                ],
            },
            {
                "key": "step6",
                "title": "Implementation & Consensus",
                "intro": "यदि MAPS ले यो सिफारिस सार्वजनिक गर्यो भने अधिकांश क्लिनिकहरूले व्यवहारिक रूपमा लागू गर्न सक्लान्? अब कृपया आफ्नो सहमतिको स्तर जनाउनुहोस्।",
                "sections": [
                    {
                        "type": "radio",
                        "name": "implementation",
                        "label": "Implementation Considerations",
                        "options": [
                            ("immediate", "तत्काल लागू गर्न सकिने"),
                            ("phased", "चरणबद्ध रूपमा लागू गर्नुपर्ने"),
                            ("other", "अन्य"),
                        ],
                    },
                    {
                        "type": "radio",
                        "name": "consensus",
                        "label": "Consensus Check",
                        "options": [
                            ("full", "पूर्ण सहमत"),
                            ("with_suggestions", "केही सुझावसहित सहमत"),
                            ("disagree", "असहमत"),
                        ],
                    },
                    {"type": "text", "name": "facilitator_name", "label": "Facilitator नाम"},
                ],
            },
        ],
    },
    "session2": {
        "title": "दिगो तथा न्यायोचित फिजियोथेरापी सेवा शुल्क (Sustainable & Fair Physiotherapy Service Pricing)",
        "short_title": "Session 2: Service Pricing",
        "steps": [
            {
                "key": "step1",
                "title": "Root Cause Identification",
                "intro": "मध्यपुरका विभिन्न क्लिनिकहरूमा फिजियोथेरापी सेवा शुल्क फरक हुनुको मुख्य कारण के हो?",
                "sections": [
                    {
                        "type": "checklist_other",
                        "name": "causes",
                        "label": "Key Issues Identified",
                        "options": [
                            ("high_competition", "High Competition"),
                            ("operational_cost", "Different Operational Cost"),
                            ("purchasing_capacity", "Patient Purchasing Capacity"),
                            ("no_common_framework", "No Common Pricing Framework"),
                            ("service_quality", "Different Service Quality"),
                            ("session_duration", "Different Session Duration"),
                            ("therapist_qualification", "Therapist Qualification"),
                            ("experience_difference", "Experience Difference"),
                            ("equipment_technology", "Equipment & Technology"),
                            ("market_influence", "Market Influence"),
                        ],
                    },
                ],
            },
            {
                "key": "step2",
                "title": "Impact Rating (प्रभाव मूल्याङ्कन)",
                "intro": "प्रत्येक कारणले न्यायोचित तथा दिगो सेवा शुल्क निर्धारणमा कति प्रभाव पारिरहेको छ भन्ने आधारमा १ देखि ५ सम्म अंक दिनुहोस्, अनि शीर्ष तीन कारणमा सहमति गर्नुहोस्।",
                "sections": [
                    {
                        "type": "score_for_prior",
                        "name": "impact_scores",
                        "label": "Impact Score (1 = Very Low ... 5 = Very High)",
                        "source_step": "step1",
                        "source_field": "causes",
                    },
                    {
                        "type": "top_n_select",
                        "name": "top3",
                        "label": "Top 3 सबैभन्दा बढी प्रभाव पार्ने कारणहरू",
                        "source_step": "step1",
                        "source_field": "causes",
                        "n": 3,
                    },
                ],
            },
            {
                "key": "step3",
                "title": "Possible Solutions",
                "intro": "बिरामीको पहुँच, सेवाको गुणस्तर तथा क्लिनिकको आर्थिक दिगोपनलाई सन्तुलन गर्ने गरी अधिकांश क्लिनिकहरूले व्यवहारिक रूपमा अपनाउन सक्ने समाधानहरू के हुन सक्छन्?",
                "sections": [
                    {"type": "free_text", "name": "solutions_free_text", "label": "समूहबाट आएका सम्भावित समाधानहरू", "rows": 5},
                ],
            },
            {
                "key": "step4",
                "title": "Recommended Pricing Framework",
                "intro": "MAPS ले एउटा Recommended Physiotherapy Pricing Framework तयार गर्दैछ। त्यसमा के-के समावेश हुनुपर्छ, र एउटा illustrative मूल्य दायरा (NPR) पनि सुझाव दिनुहोस्।",
                "sections": [
                    {
                        "type": "checklist_other",
                        "name": "framework_items",
                        "label": "Framework Elements",
                        "options": [
                            ("recommended_price_range", "Recommended Price Range"),
                            ("initial_assessment_fee", "Initial Assessment Fee"),
                            ("followup_fee", "Follow-up Fee"),
                            ("home_visit_fee", "Home Visit Fee"),
                            ("specialized_session", "Specialized Session"),
                            ("extended_session", "Extended Session"),
                            ("package_discount", "Package Discount"),
                            ("review_interval", "Review Interval"),
                        ],
                    },
                    {
                        "type": "number_fields",
                        "name": "illustrative_pricing",
                        "label": "Illustrative Example (NPR)",
                        "fields": [
                            ("initial_assessment", "Initial Assessment", "NPR"),
                            ("followup_session", "Follow-up Session", "NPR"),
                            ("home_visit", "Home Visit", "NPR"),
                            ("specialized_session", "Specialized Session", "NPR"),
                            ("extended_session", "Extended Session (>60 Minutes)", "NPR"),
                        ],
                    },
                    {"type": "free_text", "name": "other_pricing_recommendations", "label": "Other Pricing Recommendations", "rows": 3},
                ],
            },
            {
                "key": "step5",
                "title": "Reality Check",
                "intro": "यदि MAPS ले यो Pricing Framework सिफारिस सार्वजनिक गर्यो भने अधिकांश क्लिनिकहरूले व्यवहारिक रूपमा लागू गर्न सक्लान्?",
                "sections": [
                    {
                        "type": "radio",
                        "name": "reality_check",
                        "label": "Group Evaluation",
                        "options": [
                            ("immediately_applicable", "Immediately Applicable"),
                            ("minor_modifications", "Applicable with Minor Modifications"),
                            ("phased", "Phased Implementation"),
                            ("difficult", "Difficult to Implement at Present"),
                        ],
                    },
                    {"type": "free_text", "name": "implementation_challenges", "label": "Implementation Challenges", "rows": 4},
                ],
            },
            {
                "key": "step6",
                "title": "Final Consensus",
                "intro": "कृपया आफ्नो सहमतिको स्तर जनाउनुहोस्।",
                "sections": [
                    {
                        "type": "radio",
                        "name": "consensus",
                        "label": "Consensus Check",
                        "options": [
                            ("full", "पूर्ण सहमत"),
                            ("with_suggestions", "केही सुझावसहित सहमत"),
                            ("disagree", "असहमत"),
                        ],
                    },
                    {"type": "text", "name": "facilitator_name", "label": "Facilitator नाम"},
                ],
            },
        ],
    },
    "session3": {
        "title": "न्यायोचित तथा दिगो व्यावसायिक पारिश्रमिक (Fair & Sustainable Professional Compensation)",
        "short_title": "Session 3: Professional Compensation",
        "steps": [
            {
                "key": "step1",
                "title": "Root Cause Identification",
                "intro": "मध्यपुरका विभिन्न क्लिनिकहरूमा फिजियोथेरापिस्टको पारिश्रमिक फरक हुनुको मुख्य कारण के हो?",
                "sections": [
                    {
                        "type": "checklist_other",
                        "name": "causes",
                        "label": "Key Issues Identified",
                        "options": [
                            ("patient_volume", "Patient Volume"),
                            ("operational_cost", "Operational Cost"),
                            ("no_common_salary_framework", "No Common Salary Framework"),
                            ("experience_valuation", "Experience Valuation"),
                            ("qualification_differences", "Qualification Differences"),
                            ("employment_structure", "Employment Structure"),
                        ],
                    },
                ],
            },
            {
                "key": "step2",
                "title": "Impact Rating (प्रभाव मूल्याङ्कन)",
                "intro": "प्रत्येक कारणले पारिश्रमिक फरक पर्नमा कति प्रभाव पारिरहेको छ भन्ने आधारमा १ देखि ५ सम्म अंक दिनुहोस्, अनि शीर्ष तीन कारणमा सहमति गर्नुहोस्।",
                "sections": [
                    {
                        "type": "score_for_prior",
                        "name": "impact_scores",
                        "label": "Impact Score (1 = Very Low ... 5 = Very High)",
                        "source_step": "step1",
                        "source_field": "causes",
                    },
                    {
                        "type": "top_n_select",
                        "name": "top3",
                        "label": "Top 3 सबैभन्दा बढी प्रभाव पार्ने कारणहरू",
                        "source_step": "step1",
                        "source_field": "causes",
                        "n": 3,
                    },
                ],
            },
            {
                "key": "step3",
                "title": "Possible Solutions",
                "intro": "यी कारणहरूलाई ध्यानमा राख्दा, अधिकांश क्लिनिकहरूले व्यवहारिक रूपमा लागू गर्न सक्ने समाधानहरू के हुन सक्छन्?",
                "sections": [
                    {"type": "free_text", "name": "solutions_free_text", "label": "समूहबाट आएका सम्भावित समाधानहरू", "rows": 5},
                ],
            },
            {
                "key": "step4",
                "title": "Recommended Compensation Model",
                "intro": "MAPS ले एउटा Recommended Compensation Model तयार गर्दैछ। त्यसमा के-के समावेश हुनुपर्छ, र लागू भए संरचना (Structure) कस्तो हुनुपर्छ?",
                "sections": [
                    {
                        "type": "checklist_other",
                        "name": "model_elements",
                        "label": "Model Elements",
                        "options": [
                            ("minimum_salary", "Minimum Salary"),
                            ("salary_range", "Salary Range"),
                            ("qualification_based", "Qualification-Based Structure"),
                            ("experience_based", "Experience-Based Progression"),
                            ("performance_incentive", "Performance Incentive"),
                            ("revenue_sharing", "Revenue / Percentage Sharing"),
                            ("bonus_system", "Bonus System"),
                            ("fixed_plus_incentive", "Fixed Salary + Incentive"),
                        ],
                    },
                    {
                        "type": "number_fields",
                        "name": "fixed_salary",
                        "label": "Fixed Salary Model (NPR)",
                        "fields": [
                            ("fresh_bpt", "Fresh BPT", "NPR"),
                            ("years_3_5", "3–5 Years Experience", "NPR"),
                            ("mpt", "MPT", "NPR"),
                            ("senior_physio", "Senior Physiotherapist", "NPR"),
                        ],
                    },
                    {
                        "type": "number_fields",
                        "name": "fixed_plus_incentive",
                        "label": "Fixed Salary + Incentive Model",
                        "fields": [
                            ("base_salary", "Base Salary", "NPR"),
                        ],
                    },
                    {
                        "type": "text_fields",
                        "name": "incentive_details",
                        "label": "Incentive Basis / Structure",
                        "fields": [
                            ("incentive_basis", "Incentive Basis (Per Patient / Revenue % / Performance Indicators / Other)"),
                            ("incentive_structure", "Incentive Structure"),
                        ],
                    },
                    {
                        "type": "number_fields",
                        "name": "revenue_sharing",
                        "label": "Revenue Sharing Model",
                        "fields": [
                            ("clinic_share", "Clinic Share", "%"),
                            ("physio_share", "Physiotherapist Share", "%"),
                        ],
                    },
                    {
                        "type": "number_fields",
                        "name": "qualification_based",
                        "label": "Qualification-Based Structure (NPR)",
                        "fields": [
                            ("bpt", "BPT", "NPR"),
                            ("mpt", "MPT", "NPR"),
                            ("certification", "Specialized Training / Certification", "NPR"),
                        ],
                    },
                    {
                        "type": "number_fields",
                        "name": "experience_based",
                        "label": "Experience-Based Structure (NPR)",
                        "fields": [
                            ("years_0_2", "0–2 Years", "NPR"),
                            ("years_3_5", "3–5 Years", "NPR"),
                            ("years_5_10", "5–10 Years", "NPR"),
                            ("years_10_plus", "10+ Years", "NPR"),
                        ],
                    },
                    {"type": "free_text", "name": "model_description", "label": "Model Description / Applicability Notes", "rows": 4},
                ],
            },
            {
                "key": "step5",
                "title": "Final Recommendation Summary",
                "intro": "समूहले सिफारिस गर्ने Compensation Structure संक्षेपमा लेख्नुहोस्।",
                "sections": [
                    {"type": "free_text", "name": "key_solutions", "label": "Key Solutions", "rows": 4},
                    {"type": "free_text", "name": "recommended_model_summary", "label": "Recommended Compensation Model (सारांश)", "rows": 4},
                ],
            },
            {
                "key": "step6",
                "title": "Implementation & Consensus",
                "intro": "कृपया आफ्नो सहमतिको स्तर जनाउनुहोस्।",
                "sections": [
                    {
                        "type": "radio",
                        "name": "implementation",
                        "label": "Implementation Considerations",
                        "options": [
                            ("immediate", "तत्काल लागू गर्न सकिने"),
                            ("phased", "चरणबद्ध रूपमा लागू गर्नुपर्ने"),
                            ("other", "अन्य"),
                        ],
                    },
                    {
                        "type": "radio",
                        "name": "consensus",
                        "label": "Consensus Check",
                        "options": [
                            ("full", "पूर्ण सहमत"),
                            ("with_suggestions", "केही सुझावसहित सहमत"),
                            ("disagree", "असहमत"),
                        ],
                    },
                    {"type": "text", "name": "facilitator_name", "label": "Facilitator नाम"},
                ],
            },
        ],
    },
}


def get_session(session_key):
    return SESSIONS.get(session_key)


def get_step(session_key, step_no):
    session = get_session(session_key)
    if not session:
        return None
    steps = session["steps"]
    if step_no < 1 or step_no > len(steps):
        return None
    return steps[step_no - 1]


def get_step_by_key(session_key, step_key):
    session = get_session(session_key)
    if not session:
        return None
    for step in session["steps"]:
        if step["key"] == step_key:
            return step
    return None


def get_section(step, section_name):
    if not step:
        return None
    for section in step["sections"]:
        if section["name"] == section_name:
            return section
    return None


def get_section_options(session_key, step_key, section_name):
    """Look up the (key, label) options a checklist_other section defined,
    so a later step (score_for_prior / top_n_select) can render human labels
    for the causes/items chosen earlier."""
    step = get_step_by_key(session_key, step_key)
    section = get_section(step, section_name)
    if not section:
        return []
    return section.get("options", [])

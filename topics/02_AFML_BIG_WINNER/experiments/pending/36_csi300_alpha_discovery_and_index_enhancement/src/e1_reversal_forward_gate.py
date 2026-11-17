"""Strict date-consistency layer for pending forward intake; not a PIT certifier."""
import pandas as pd
from e1_reversal_validation import forward_eligibility
def validate_metadata(record,frozen_signal_date,protocol_hash,registration_at):
 ok,reason=forward_eligibility(record,frozen_signal_date,protocol_hash)
 if not ok:return ok,reason
 try:
  signal=pd.Timestamp(record['signal_date']).date()
  decision=pd.Timestamp(record['signal_decision_at']).tz_convert('Asia/Shanghai')
  generated=pd.Timestamp(record['generated_at'])
  entry=pd.Timestamp(record['entry_at']).tz_convert('Asia/Shanghai')
  registration=pd.Timestamp(registration_at)
  if registration.tzinfo is None:return False,'REGISTRATION_TIMEZONE_REQUIRED'
  if decision.date()!=signal:return False,'SIGNAL_DECISION_DATE_MISMATCH'
  if generated<=registration or decision<=registration:return False,'PRE_REGISTRATION_RECORD'
  if entry.date()<=signal:return False,'ENTRY_NOT_AFTER_SIGNAL_DAY'
 except (ValueError,TypeError):return False,'INVALID_METADATA'
 return True,'METADATA_ELIGIBLE_REQUIRES_CALENDAR_AND_RECEIPT_VERIFICATION'

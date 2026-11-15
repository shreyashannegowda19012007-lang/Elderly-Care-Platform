"""
Domain models and data structures for GoldenCare Platform.
Provides strongly-typed dataclasses and TypedDict definitions for
Users, Medications, AdherenceLogs, Appointments, VitalsLogs, Alerts,
and DrugInteractions.
"""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict, Union


# ==========================================
# TypedDict Definitions for Dictionary APIs
# ==========================================

class UserDict(TypedDict, total=False):
    id: int
    role: str
    name: str
    passcode: str
    phone: Optional[str]
    email: Optional[str]
    emergency_contact_name: Optional[str]
    emergency_contact_phone: Optional[str]
    notes: Optional[str]
    created_at: Optional[str]


class MedicationDict(TypedDict, total=False):
    id: int
    patient_id: int
    name: str
    dosage: str
    frequency: str
    time_of_day: str
    scheduled_time: str
    pill_color: str
    pill_shape: str
    instructions: Optional[str]
    stock_remaining: int
    refill_threshold: int
    is_active: int
    created_at: Optional[str]


class AdherenceLogDict(TypedDict, total=False):
    id: int
    medication_id: int
    patient_id: int
    scheduled_date: str
    scheduled_time: str
    taken_at: Optional[str]
    status: str
    notes: Optional[str]
    recorded_by: str
    created_at: Optional[str]


class AppointmentDict(TypedDict, total=False):
    id: int
    patient_id: int
    title: str
    doctor_name: str
    clinic_address: str
    appointment_date: str
    appointment_time: str
    transport_required: int
    prep_notes: Optional[str]
    status: str
    created_at: Optional[str]


class VitalsLogDict(TypedDict, total=False):
    id: int
    patient_id: int
    recorded_date: str
    recorded_time: str
    systolic_bp: Optional[int]
    diastolic_bp: Optional[int]
    blood_glucose: Optional[float]
    heart_rate: Optional[int]
    weight_kg: Optional[float]
    mood: str
    notes: Optional[str]
    is_abnormal: int
    created_at: Optional[str]


class AlertDict(TypedDict, total=False):
    id: int
    patient_id: int
    medication_id: Optional[int]
    alert_type: str
    severity: str
    message: str
    recipient_email: Optional[str]
    delivery_status: str
    sent_at: Optional[str]


class DrugInteractionDict(TypedDict, total=False):
    id: int
    drug_a: str
    drug_b: str
    severity: str
    description: str
    recommendation: str


# ==========================================
# Strongly-Typed Dataclass Domain Models
# ==========================================

@dataclass
class User:
    """Represents a system user (Senior Patient, Family Caregiver, or Clinical Admin)."""
    name: str
    role: str  # 'elderly' | 'caretaker' | 'admin'
    passcode: str
    id: Optional[int] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert dataclass instance to a standard dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> User:
        """Create a User instance from a dictionary."""
        return cls(
            id=data.get("id"),
            name=data["name"],
            role=data["role"],
            passcode=data["passcode"],
            phone=data.get("phone"),
            email=data.get("email"),
            emergency_contact_name=data.get("emergency_contact_name"),
            emergency_contact_phone=data.get("emergency_contact_phone"),
            notes=data.get("notes"),
            created_at=data.get("created_at"),
        )

    @classmethod
    def from_row(cls, row: Union[sqlite3.Row, Dict[str, Any]]) -> User:
        """Create a User instance from an SQLite Row or Dict."""
        return cls.from_dict(dict(row))


@dataclass
class Medication:
    """Represents a prescribed medication regimen and inventory tracking."""
    patient_id: int
    name: str
    dosage: str
    frequency: str
    time_of_day: str
    scheduled_time: str
    id: Optional[int] = None
    pill_color: str = "#2563EB"
    pill_shape: str = "Tablet"
    instructions: Optional[str] = None
    stock_remaining: int = 30
    refill_threshold: int = 5
    is_active: int = 1
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert dataclass instance to a standard dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Medication:
        """Create a Medication instance from a dictionary."""
        return cls(
            id=data.get("id"),
            patient_id=data["patient_id"],
            name=data["name"],
            dosage=data["dosage"],
            frequency=data["frequency"],
            time_of_day=data["time_of_day"],
            scheduled_time=data["scheduled_time"],
            pill_color=data.get("pill_color", "#2563EB"),
            pill_shape=data.get("pill_shape", "Tablet"),
            instructions=data.get("instructions"),
            stock_remaining=data.get("stock_remaining", 30),
            refill_threshold=data.get("refill_threshold", 5),
            is_active=data.get("is_active", 1),
            created_at=data.get("created_at"),
        )

    @classmethod
    def from_row(cls, row: Union[sqlite3.Row, Dict[str, Any]]) -> Medication:
        """Create a Medication instance from an SQLite Row or Dict."""
        return cls.from_dict(dict(row))


@dataclass
class AdherenceLog:
    """Represents a scheduled medication slot and actual intake status."""
    medication_id: int
    patient_id: int
    scheduled_date: str
    scheduled_time: str
    id: Optional[int] = None
    taken_at: Optional[str] = None
    status: str = "PENDING"  # TAKEN, MISSED, PENDING, SKIPPED
    notes: Optional[str] = None
    recorded_by: str = "elderly"
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert dataclass instance to a standard dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AdherenceLog:
        """Create an AdherenceLog instance from a dictionary."""
        return cls(
            id=data.get("id"),
            medication_id=data["medication_id"],
            patient_id=data["patient_id"],
            scheduled_date=data["scheduled_date"],
            scheduled_time=data["scheduled_time"],
            taken_at=data.get("taken_at"),
            status=data.get("status", "PENDING"),
            notes=data.get("notes"),
            recorded_by=data.get("recorded_by", "elderly"),
            created_at=data.get("created_at"),
        )

    @classmethod
    def from_row(cls, row: Union[sqlite3.Row, Dict[str, Any]]) -> AdherenceLog:
        """Create an AdherenceLog instance from an SQLite Row or Dict."""
        return cls.from_dict(dict(row))


@dataclass
class Appointment:
    """Represents a clinical doctor consultation or health examination."""
    patient_id: int
    title: str
    doctor_name: str
    clinic_address: str
    appointment_date: str
    appointment_time: str
    id: Optional[int] = None
    transport_required: int = 0
    prep_notes: Optional[str] = None
    status: str = "SCHEDULED"  # SCHEDULED, COMPLETED, CANCELLED
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert dataclass instance to a standard dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Appointment:
        """Create an Appointment instance from a dictionary."""
        return cls(
            id=data.get("id"),
            patient_id=data["patient_id"],
            title=data["title"],
            doctor_name=data["doctor_name"],
            clinic_address=data["clinic_address"],
            appointment_date=data["appointment_date"],
            appointment_time=data["appointment_time"],
            transport_required=data.get("transport_required", 0),
            prep_notes=data.get("prep_notes"),
            status=data.get("status", "SCHEDULED"),
            created_at=data.get("created_at"),
        )

    @classmethod
    def from_row(cls, row: Union[sqlite3.Row, Dict[str, Any]]) -> Appointment:
        """Create an Appointment instance from an SQLite Row or Dict."""
        return cls.from_dict(dict(row))


@dataclass
class VitalsLog:
    """Represents daily physiological telemetry (blood pressure, glucose, pulse, weight)."""
    patient_id: int
    recorded_date: str
    recorded_time: str
    id: Optional[int] = None
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None
    blood_glucose: Optional[float] = None
    heart_rate: Optional[int] = None
    weight_kg: Optional[float] = None
    mood: str = "Good"
    notes: Optional[str] = None
    is_abnormal: int = 0
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert dataclass instance to a standard dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> VitalsLog:
        """Create a VitalsLog instance from a dictionary."""
        return cls(
            id=data.get("id"),
            patient_id=data["patient_id"],
            recorded_date=data["recorded_date"],
            recorded_time=data["recorded_time"],
            systolic_bp=data.get("systolic_bp"),
            diastolic_bp=data.get("diastolic_bp"),
            blood_glucose=data.get("blood_glucose"),
            heart_rate=data.get("heart_rate"),
            weight_kg=data.get("weight_kg"),
            mood=data.get("mood", "Good"),
            notes=data.get("notes"),
            is_abnormal=data.get("is_abnormal", 0),
            created_at=data.get("created_at"),
        )

    @classmethod
    def from_row(cls, row: Union[sqlite3.Row, Dict[str, Any]]) -> VitalsLog:
        """Create a VitalsLog instance from an SQLite Row or Dict."""
        return cls.from_dict(dict(row))


@dataclass
class Alert:
    """Represents an automated or manual alert notification and audit entry."""
    patient_id: int
    alert_type: str
    severity: str  # INFO, WARNING, CRITICAL
    message: str
    id: Optional[int] = None
    medication_id: Optional[int] = None
    recipient_email: Optional[str] = None
    delivery_status: str = "SENT"  # SENT, LOGGED, FAILED
    sent_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert dataclass instance to a standard dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Alert:
        """Create an Alert instance from a dictionary."""
        return cls(
            id=data.get("id"),
            patient_id=data["patient_id"],
            alert_type=data["alert_type"],
            severity=data["severity"],
            message=data["message"],
            medication_id=data.get("medication_id"),
            recipient_email=data.get("recipient_email"),
            delivery_status=data.get("delivery_status", "SENT"),
            sent_at=data.get("sent_at"),
        )

    @classmethod
    def from_row(cls, row: Union[sqlite3.Row, Dict[str, Any]]) -> Alert:
        """Create an Alert instance from an SQLite Row or Dict."""
        return cls.from_dict(dict(row))


# Alias AlertLog to Alert for full naming flexibility
AlertLog = Alert


@dataclass
class DrugInteraction:
    """Represents a pairwise drug-drug contraindication rule."""
    drug_a: str
    drug_b: str
    severity: str  # High, Moderate, Minor
    description: str
    recommendation: str
    id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert dataclass instance to a standard dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DrugInteraction:
        """Create a DrugInteraction instance from a dictionary."""
        return cls(
            id=data.get("id"),
            drug_a=data["drug_a"],
            drug_b=data["drug_b"],
            severity=data["severity"],
            description=data["description"],
            recommendation=data["recommendation"],
        )

    @classmethod
    def from_row(cls, row: Union[sqlite3.Row, Dict[str, Any]]) -> DrugInteraction:
        """Create a DrugInteraction instance from an SQLite Row or Dict."""
        return cls.from_dict(dict(row))

"""Mapping between the HTTP wire models and application DTOs.

Canonical: .pi/architecture/modules/stakeholder-model.md
"""

from __future__ import annotations

from stakeholder_model.application.commands import (
    CitePowerSourceRequest,
    RecordHistoricalPositionRequest,
    RegisterStakeholderRequest,
    UpdateStakeholderProfileRequest,
)
from stakeholder_model.application.dto import (
    HistoricalPositionResult,
    StakeholderProfileResult,
    StakeholderSummaryResult,
)
from stakeholder_model.domain.values import (
    BudgetLimit,
    Constraint,
    DecisionPriority,
    InstitutionIdentity,
    Interest,
    MandateScope,
    MandateSource,
    PassageId,
    StakeholderId,
    VetoRight,
)
from stakeholder_model.interfaces.http.schemas import (
    BudgetBody,
    CitePowerSourceBody,
    ConstraintBody,
    HistoricalPositionBody,
    InstitutionBody,
    InterestBody,
    MandateScopeBody,
    MandateSourceBody,
    PositionResponse,
    PriorityBody,
    RegisterStakeholderBody,
    StakeholderProfileResponse,
    StakeholderSummaryResponse,
    UpdateProfileBody,
    VetoRightBody,
)


def to_identity(body: InstitutionBody) -> InstitutionIdentity:
    return InstitutionIdentity(
        name=body.name,
        short_name=body.short_name,
        category=body.category,
        code=body.code,
    )


def to_source(body: MandateSourceBody) -> MandateSource:
    return MandateSource(kind=body.kind, citation=body.citation, as_of=body.as_of)


def to_interest(body: InterestBody) -> Interest:
    return Interest(topic=body.topic, goal=body.goal, weight=body.weight)


def to_constraint(body: ConstraintBody) -> Constraint:
    return Constraint(statement=body.statement, topic=body.topic)


def to_priority(body: PriorityBody) -> DecisionPriority:
    return DecisionPriority(rank=body.rank, topic=body.topic)


def to_veto(body: VetoRightBody) -> VetoRight:
    return VetoRight(proposal_class=body.proposal_class, source=to_source(body.source))


def to_register_request(body: RegisterStakeholderBody) -> RegisterStakeholderRequest:
    return RegisterStakeholderRequest(
        identity=to_identity(body.identity),
        mandate_scope=MandateScope(
            topics=frozenset(body.mandate_scope.topics),
            description=body.mandate_scope.description,
            source=to_source(body.mandate_scope.source),
        ),
        budget=BudgetLimit(
            amount_eur=body.budget.amount_eur,
            period=body.budget.period,
            tolerance=body.budget.tolerance,
            source=to_source(body.budget.source),
        ),
        interests=tuple(to_interest(item) for item in body.interests),
        constraints=tuple(to_constraint(item) for item in body.constraints),
        priorities=tuple(to_priority(item) for item in body.priorities),
        veto_rights=tuple(to_veto(item) for item in body.veto_rights),
    )


def to_update_request(
    stakeholder_id: str, body: UpdateProfileBody
) -> UpdateStakeholderProfileRequest:
    return UpdateStakeholderProfileRequest(
        stakeholder_id=StakeholderId(stakeholder_id),
        interests=(
            tuple(to_interest(item) for item in body.interests)
            if body.interests is not None
            else None
        ),
        constraints=(
            tuple(to_constraint(item) for item in body.constraints)
            if body.constraints is not None
            else None
        ),
        priorities=(
            tuple(to_priority(item) for item in body.priorities)
            if body.priorities is not None
            else None
        ),
        red_lines=tuple(body.red_lines) if body.red_lines is not None else None,
        expected_version=body.expected_version,
    )


def to_cite_request(stakeholder_id: str, body: CitePowerSourceBody) -> CitePowerSourceRequest:
    return CitePowerSourceRequest(
        stakeholder_id=StakeholderId(stakeholder_id),
        power_type=body.power_type,
        source=MandateSource(kind=body.kind, citation=body.citation, as_of=body.as_of),
        proposal_class=body.proposal_class,
    )


def to_record_request(
    stakeholder_id: str, body: HistoricalPositionBody
) -> RecordHistoricalPositionRequest:
    return RecordHistoricalPositionRequest(
        stakeholder_id=StakeholderId(stakeholder_id),
        stance=body.stance,
        attribution=body.attribution,
        stated_on=body.stated_on,
        passage_id=PassageId(body.passage_id),
    )


def to_summary_response(result: StakeholderSummaryResult) -> StakeholderSummaryResponse:
    return StakeholderSummaryResponse(
        stakeholder_id=result.stakeholder_id,
        identity=InstitutionBody(
            name=result.identity.name,
            short_name=result.identity.short_name,
            category=result.identity.category,
            code=result.identity.code,
        ),
        interest_count=result.interest_count,
        constraint_count=result.constraint_count,
        profile_version=result.profile_version,
    )


def to_position_response(result: HistoricalPositionResult) -> PositionResponse:
    return PositionResponse(
        position_id=result.position_id,
        stakeholder_id=result.stakeholder_id,
        stance=result.stance,
        attribution=result.attribution,
        stated_on=result.stated_on,
        passage_id=result.passage_id,
        usable=result.usable,
    )


def to_profile_response(result: StakeholderProfileResult) -> StakeholderProfileResponse:
    profile = result.profile
    return StakeholderProfileResponse(
        stakeholder_id=result.stakeholder_id,
        identity=InstitutionBody(
            name=result.identity.name,
            short_name=result.identity.short_name,
            category=result.identity.category,
            code=result.identity.code,
        ),
        mandate_scope=MandateScopeBody(
            topics=sorted(profile.mandate_scope.topics),
            description=profile.mandate_scope.description,
            source=MandateSourceBody(
                kind=profile.mandate_scope.source.kind,
                citation=profile.mandate_scope.source.citation,
                as_of=profile.mandate_scope.source.as_of,
            ),
        ),
        budget=BudgetBody(
            amount_eur=profile.budget.amount_eur,
            period=profile.budget.period,
            tolerance=profile.budget.tolerance,
            source=MandateSourceBody(
                kind=profile.budget.source.kind,
                citation=profile.budget.source.citation,
                as_of=profile.budget.source.as_of,
            ),
        ),
        interests=[
            InterestBody(topic=item.topic, goal=item.goal, weight=item.weight)
            for item in profile.interests
        ],
        constraints=[
            ConstraintBody(statement=item.statement, topic=item.topic)
            for item in profile.constraints
        ],
        priorities=[PriorityBody(rank=item.rank, topic=item.topic) for item in profile.priorities],
        red_lines=list(profile.red_lines),
        veto_rights=[
            VetoRightBody(
                proposal_class=item.proposal_class,
                source=MandateSourceBody(
                    kind=item.source.kind,
                    citation=item.source.citation,
                    as_of=item.source.as_of,
                ),
            )
            for item in result.veto_rights
        ],
        positions=[
            to_position_response(
                HistoricalPositionResult(
                    position_id=position.id,
                    stakeholder_id=result.stakeholder_id,
                    stance=position.stance,
                    attribution=position.attribution,
                    stated_on=position.stated_on,
                    passage_id=position.passage_id,
                    usable=position.usable,
                )
            )
            for position in result.positions
        ],
        profile_version=profile.version,
    )

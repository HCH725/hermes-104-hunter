"""Pydantic data models for hermes-104-hunter."""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class JobSearchResult(BaseModel):
    job_id: str = Field(description="職缺英數字代碼 (slug，如 8nd15)")
    job_no: int | None = Field(default=None, description="104 內部十進位職缺編號 (如 14526905)")
    title: str = Field(description="職缺名稱")
    company_name: str = Field(description="公司名稱")
    area: str = Field(description="工作地點地區")
    salary: str = Field(description="薪資文字描述")
    salary_min: int | None = Field(default=None, description="薪資下限（若有數字）")
    salary_max: int | None = Field(default=None, description="薪資上限（若有數字）")
    is_negotiable: bool = Field(default=False, description="是否為面議")
    experience: str = Field(default="不拘", description="經歷要求")
    education: str = Field(default="不拘", description="學歷要求")
    tags: list[str] = Field(default_factory=list, description="職缺標籤（如遠端、外商等）")
    update_date: str = Field(default="", description="更新日期")
    url: str = Field(description="104 職缺網址")


class SearchJobsResponse(BaseModel):
    keyword: str
    total_count: int
    page: int
    page_size: int
    total_pages: int
    jobs: list[JobSearchResult]


class JobDetail(BaseModel):
    job_id: str
    job_no: int | None = None
    title: str
    company_name: str
    description: str
    salary: str
    work_type: str
    location: str
    experience_req: str
    education_req: str
    major_req: list[str] = Field(default_factory=list)
    language_req: list[str] = Field(default_factory=list)
    skills_req: list[str] = Field(default_factory=list)
    certificates_req: list[str] = Field(default_factory=list)
    other_requirements: str = ""
    welfare: str = ""
    hr_contact: str | None = None
    is_applied: bool | None = None
    analysis_type: int | None = None
    url: str


class DimensionItem(BaseModel):
    name: str
    count: int | None = None
    percent: float


class LanguageItem(BaseModel):
    name: str
    count: int | None = None
    percent: float
    levels: list[DimensionItem] = Field(default_factory=list)


class ApplyAnalysisResult(BaseModel):
    job_id: str
    job_no: int
    total_applicants: int | None = Field(
        description="數學逆推算出的精準總應徵人數；僅在 total_basis='inferred' 時才可視為精算值"
    )
    total_basis: Literal["inferred", "exact", "unknown"] = Field(description="計算依據：inferred 代表演算法逆推成功")
    estimated_applicants: int | None = Field(
        default=None,
        description="無精確整數解時的『最小誤差概估』，僅供參考，絕不可當作精算人數引用",
    )
    estimate_note: str = Field(default="", description="概估說明與信心限制，回答時應一併轉述")
    candidate_counts: list[int] = Field(default_factory=list, description="符合百分比公倍數的可能人數解（依吻合度排序）")
    apply_range: str = Field(description="104 官方標籤區間（如 11~30 人、30 人以上）")
    update_time: str
    education: list[DimensionItem] = Field(default_factory=list, description="對手學歷分佈")
    age_distribution: list[DimensionItem] = Field(default_factory=list, description="對手年齡分佈")
    experience_distribution: list[DimensionItem] = Field(default_factory=list, description="對手年資經歷分佈")
    languages: list[LanguageItem] = Field(default_factory=list, description="對手語言能力分佈")
    top_majors: list[DimensionItem] = Field(default_factory=list, description="對手主修科系分佈 Top 10")
    top_skills: list[DimensionItem] = Field(default_factory=list, description="對手具備技能 Top 10（重要情報：突圍關鍵！）")
    certificates: list[DimensionItem] = Field(default_factory=list, description="對手具備證照分佈")


class CoverLetterTemplate(BaseModel):
    title: str
    content: str
    is_default: bool = False


class ApplicationPrepResult(BaseModel):
    status: Literal["ready", "already_applied", "job_closed", "error"]
    dry_run: bool
    message: str
    job_url: str
    selected_template: str
    cover_letter_filled: bool
    cover_letter_preview: str
    screenshot_path: str | None = None

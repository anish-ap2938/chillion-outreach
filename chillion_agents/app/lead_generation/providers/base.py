"""People search provider abstraction."""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..models import FinanceContact


class PeopleSearchProvider(ABC):
    """
    Look up decision makers at a company.

    HTTP details stay inside concrete providers. This interface returns
    internal FinanceContact objects only.
    """

    @abstractmethod
    def search_people(
        self,
        company_name: str,
        company_domain: Optional[str],
        target_titles: List[str],
        max_results: int,
        find_emails: bool = True,
    ) -> List[FinanceContact]:
        """
        Find people matching titles at the given company domain.

        Args:
            company_name: Display/company association name
            company_domain: Employer domain (e.g. microsoft.com). Must not be guessed.
            target_titles: Job titles to match
            max_results: Hard cap on returned contacts
            find_emails: When False, never expose/store emails even if the provider returns them
        """
        raise NotImplementedError

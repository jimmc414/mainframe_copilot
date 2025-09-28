"""
LLM Handler for AI Integration
Manages interactions with language models for mainframe assistance
"""

import os
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import json

# Support multiple LLM providers
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class AIResponse:
    """Response from AI model"""
    content: str
    command: Optional[str] = None
    explanation: Optional[str] = None
    jcl: Optional[str] = None
    confidence: float = 0.0


class LLMHandler:
    """Handler for LLM interactions"""

    def __init__(self, provider: str = "anthropic", api_key: Optional[str] = None):
        """
        Initialize LLM handler

        Args:
            provider: LLM provider (anthropic or openai)
            api_key: API key (or from environment)
        """
        self.provider = provider.lower()
        self.client = None
        self.system_prompt = self._build_system_prompt()

        # Initialize provider
        if self.provider == "anthropic" and ANTHROPIC_AVAILABLE:
            api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                self.client = anthropic.Anthropic(api_key=api_key)
                logger.info("Initialized Anthropic client")
            else:
                logger.warning("No Anthropic API key found")

        elif self.provider == "openai" and OPENAI_AVAILABLE:
            api_key = api_key or os.getenv("OPENAI_API_KEY")
            if api_key:
                openai.api_key = api_key
                self.client = openai
                logger.info("Initialized OpenAI client")
            else:
                logger.warning("No OpenAI API key found")

        else:
            logger.error(f"Provider {provider} not available or not supported")

    def _build_system_prompt(self) -> str:
        """
        Build system prompt for mainframe context

        Returns:
            str: System prompt
        """
        return """You are an expert mainframe assistant specializing in MVS 3.8J, TSO, ISPF, and JCL.
You help users with:
- Writing and debugging JCL
- TSO/ISPF commands and navigation
- Dataset management and operations
- Job submission and monitoring
- System administration tasks
- Troubleshooting mainframe issues

When providing JCL, ensure it follows proper formatting:
- Columns 1-2: // for JCL statements, /* for comments
- Column 3-71: JCL content
- Column 72: Continuation character if needed
- Use proper dataset naming conventions

When suggesting TSO commands, provide the exact command syntax.
Always explain what the command or JCL will do.

If asked to create JCL, provide complete, ready-to-run JCL with proper job cards."""

    async def process_query(self, query: str, context: Optional[str] = None) -> AIResponse:
        """
        Process user query and generate response

        Args:
            query: User question or request
            context: Additional context (e.g., screen content)

        Returns:
            AIResponse: Structured response
        """
        if not self.client:
            return AIResponse(
                content="AI assistant not configured. Please set API key.",
                confidence=0.0
            )

        try:
            # Build prompt with context
            full_prompt = query
            if context:
                full_prompt = f"Context:\n{context}\n\nQuery: {query}"

            # Get response based on provider
            if self.provider == "anthropic":
                response = await self._get_anthropic_response(full_prompt)
            elif self.provider == "openai":
                response = await self._get_openai_response(full_prompt)
            else:
                response = AIResponse(content="Provider not supported", confidence=0.0)

            return response

        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return AIResponse(
                content=f"Error processing request: {str(e)}",
                confidence=0.0
            )

    async def _get_anthropic_response(self, prompt: str) -> AIResponse:
        """
        Get response from Anthropic Claude

        Args:
            prompt: User prompt

        Returns:
            AIResponse: Structured response
        """
        try:
            message = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=2000,
                temperature=0.7,
                system=self.system_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            content = message.content[0].text
            return self._parse_response(content)

        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise

    async def _get_openai_response(self, prompt: str) -> AIResponse:
        """
        Get response from OpenAI

        Args:
            prompt: User prompt

        Returns:
            AIResponse: Structured response
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.7
            )

            content = response.choices[0].message.content
            return self._parse_response(content)

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    def _parse_response(self, content: str) -> AIResponse:
        """
        Parse LLM response into structured format

        Args:
            content: Raw response text

        Returns:
            AIResponse: Structured response
        """
        response = AIResponse(content=content, confidence=0.8)

        # Try to extract JCL if present
        if "//JOB" in content or "//" in content[:10]:
            jcl_start = content.find("//")
            if jcl_start != -1:
                jcl_end = content.find("\n\n", jcl_start)
                if jcl_end == -1:
                    jcl_end = len(content)
                response.jcl = content[jcl_start:jcl_end].strip()

        # Try to extract TSO commands
        command_markers = ["TSO>", "COMMAND:", "Execute:", "Run:"]
        for marker in command_markers:
            if marker in content:
                cmd_start = content.find(marker) + len(marker)
                cmd_end = content.find("\n", cmd_start)
                if cmd_end != -1:
                    response.command = content[cmd_start:cmd_end].strip()
                    break

        return response

    def generate_jcl(self, job_type: str, parameters: Dict[str, Any]) -> str:
        """
        Generate JCL based on job type and parameters

        Args:
            job_type: Type of job (copy, sort, compile, etc.)
            parameters: Job parameters

        Returns:
            str: Generated JCL
        """
        templates = {
            "copy": self._jcl_copy_template,
            "sort": self._jcl_sort_template,
            "compile": self._jcl_compile_template,
            "allocate": self._jcl_allocate_template,
            "delete": self._jcl_delete_template
        }

        template_func = templates.get(job_type.lower())
        if template_func:
            return template_func(parameters)
        else:
            return f"// JCL template for {job_type} not available"

    def _jcl_copy_template(self, params: Dict[str, Any]) -> str:
        """Generate copy JCL"""
        jobname = params.get('jobname', 'COPYJOB')[:8]
        input_ds = params.get('input', 'INPUT.DATASET')
        output_ds = params.get('output', 'OUTPUT.DATASET')

        return f"""//{jobname} JOB (ACCT),'COPY JOB',
//         CLASS=A,MSGCLASS=X,
//         NOTIFY=&SYSUID,MSGLEVEL=(1,1)
//*
//COPY01   EXEC PGM=IEBGENER
//SYSPRINT DD SYSOUT=*
//SYSIN    DD DUMMY
//SYSUT1   DD DSN={input_ds},DISP=SHR
//SYSUT2   DD DSN={output_ds},
//         DISP=(NEW,CATLG,DELETE),
//         SPACE=(TRK,(5,5)),
//         DCB=(RECFM=FB,LRECL=80,BLKSIZE=0)"""

    def _jcl_sort_template(self, params: Dict[str, Any]) -> str:
        """Generate sort JCL"""
        jobname = params.get('jobname', 'SORTJOB')[:8]
        input_ds = params.get('input', 'INPUT.DATASET')
        output_ds = params.get('output', 'OUTPUT.DATASET')
        sort_fields = params.get('sort_fields', 'SORT FIELDS=(1,10,CH,A)')

        return f"""//{jobname} JOB (ACCT),'SORT JOB',
//         CLASS=A,MSGCLASS=X,
//         NOTIFY=&SYSUID,MSGLEVEL=(1,1)
//*
//SORT01   EXEC PGM=SORT
//SYSOUT   DD SYSOUT=*
//SORTIN   DD DSN={input_ds},DISP=SHR
//SORTOUT  DD DSN={output_ds},
//         DISP=(NEW,CATLG,DELETE),
//         SPACE=(TRK,(5,5)),
//         DCB=(RECFM=FB,LRECL=80,BLKSIZE=0)
//SYSIN    DD *
  {sort_fields}
/*"""

    def _jcl_compile_template(self, params: Dict[str, Any]) -> str:
        """Generate compile JCL"""
        jobname = params.get('jobname', 'COMPILE')[:8]
        source = params.get('source', 'SOURCE.COBOL')
        language = params.get('language', 'COBOL').upper()

        if language == 'COBOL':
            return f"""//{jobname} JOB (ACCT),'COMPILE COBOL',
//         CLASS=A,MSGCLASS=X,
//         NOTIFY=&SYSUID,MSGLEVEL=(1,1)
//*
//COBOL    EXEC PGM=IKFCBL00,REGION=4M,
//         PARM='LIST,XREF,MAP'
//SYSPRINT DD SYSOUT=*
//SYSUT1   DD UNIT=SYSDA,SPACE=(CYL,(1,1))
//SYSUT2   DD UNIT=SYSDA,SPACE=(CYL,(1,1))
//SYSUT3   DD UNIT=SYSDA,SPACE=(CYL,(1,1))
//SYSUT4   DD UNIT=SYSDA,SPACE=(CYL,(1,1))
//SYSIN    DD DSN={source},DISP=SHR
//SYSLIN   DD DSN=&&LOADSET,
//         DISP=(MOD,PASS),
//         UNIT=SYSDA,SPACE=(CYL,(1,1))"""
        else:
            return f"// Compiler for {language} not configured"

    def _jcl_allocate_template(self, params: Dict[str, Any]) -> str:
        """Generate allocation JCL"""
        jobname = params.get('jobname', 'ALLOCATE')[:8]
        dataset = params.get('dataset', 'NEW.DATASET')
        space = params.get('space', 'TRK,(10,10)')
        dsorg = params.get('dsorg', 'PS')
        recfm = params.get('recfm', 'FB')
        lrecl = params.get('lrecl', 80)

        return f"""//{jobname} JOB (ACCT),'ALLOCATE DS',
//         CLASS=A,MSGCLASS=X,
//         NOTIFY=&SYSUID,MSGLEVEL=(1,1)
//*
//ALLOC01  EXEC PGM=IEFBR14
//NEWDS    DD DSN={dataset},
//         DISP=(NEW,CATLG,DELETE),
//         SPACE=({space}),
//         DCB=(DSORG={dsorg},RECFM={recfm},LRECL={lrecl},BLKSIZE=0)"""

    def _jcl_delete_template(self, params: Dict[str, Any]) -> str:
        """Generate delete JCL"""
        jobname = params.get('jobname', 'DELETE')[:8]
        dataset = params.get('dataset', 'OLD.DATASET')

        return f"""//{jobname} JOB (ACCT),'DELETE DS',
//         CLASS=A,MSGCLASS=X,
//         NOTIFY=&SYSUID,MSGLEVEL=(1,1)
//*
//DELETE01 EXEC PGM=IEFBR14
//DELDS    DD DSN={dataset},
//         DISP=(OLD,DELETE,DELETE)"""

    def explain_screen(self, screen_content: str) -> str:
        """
        Explain mainframe screen content

        Args:
            screen_content: Screen text

        Returns:
            str: Explanation
        """
        # Identify common screen types and provide explanation
        explanations = {
            "READY": "TSO is ready to accept commands. You can enter TSO commands or start ISPF.",
            "IKJ": "This is a TSO message. Check for any error codes or status information.",
            "ISPF": "You are in the ISPF environment. Use menu options or commands to navigate.",
            "SDSF": "System Display and Search Facility - used for viewing job output and system status.",
            "JOB": "Job-related message. Check job status or submission results.",
            "ABEND": "Abnormal end - the program or job terminated with an error.",
            "PASSWORD": "System is requesting password authentication.",
            "***": "TSO message indicator. The following text is a system message."
        }

        explanation = "Screen Analysis:\n"
        for keyword, desc in explanations.items():
            if keyword in screen_content.upper():
                explanation += f"" {desc}\n"

        if explanation == "Screen Analysis:\n":
            explanation = "Standard mainframe screen. Look for command fields (===>) or menu options."

        return explanation
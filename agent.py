import os
from typing import Literal, TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.utilities import SerpAPIWrapper
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langchain_core.tools import Tool
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# set llm gemini model
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.4,
)

search = SerpAPIWrapper()
tools = [
    Tool(
        name="Product_Research",
        func=search.run,
        description="Berguna untuk mencari tren pasar, kompetitor, dan data produk terkini."
    )
]

# create StateGraph
class AgentState(TypedDict):
    messages: List[HumanMessage | AIMessage | SystemMessage]
    research_data: str

# function to research data
def research_data_node(state: AgentState):
    """Function untuk research data"""
    # ambil message terakhir
    messages = state["messages"]
    last_message = messages[-1].content
    print(f"Last message: {last_message}")

    # search data dari pesan
    search_result = search.run(last_message)

    # simpan data ke state
    state["research_data"] = search_result

    return state

# function strategic data
def strategic_data_node(state: AgentState):
    """ Otak utama untuk menentukan strategi berdasarkan data yang diperoleh dan intruksi yg diberikan"""
    # ambil data dari state
    messages = state["messages"]
    research_data = state.get("research_data", "Tidak ada data riset")

    # tampilkan state research
    print(f"Data riset: {research_data}")

    system_prompt = """
    Peran: Senior Product Strategist.
    Tugas: Analisis data riset berikut.
    
    DATA RISET:
    {context}
    
    Instruksi Output (WAJIB Ikuti Format Ini):
    
    📈 **Tren dan Insight Pasar:**
    - [Insight 1]
    - [Insight 2]

    📊 **Analisis SWOT:**
    - 💪 **Strengths:** [Kekuatan]
    - ⚠️ **Weaknesses:** [Kelemahan]
    - 🌟 **Opportunities:** [Peluang]
    - ⚡ **Threats:** [Ancaman]

    🚀 **Rekomendasi Strategis:**
    - [Strategi 1]
    - [Strategi 2]

    ATURAN FORMATTING (PENTING UNTUK TELEGRAM):
    1. JANGAN gunakan simbol underscore (_) sama sekali. Ganti dengan spasi.
    2. Gunakan strip (-) untuk bullet points.
    3. Pastikan setiap tanda bintang ganda (**) selalu ditutup rapat.
    4. Jawab SINGKAT & PADAT.
    """

    system_message = SystemMessage(
        content=system_prompt.format(context=research_data)
    )

    # invoke
    response = llm.invoke([system_message] + messages)

    # simpan response ke state
    return {"messages": messages + [response]}

# function untuk bicara santai
def general_chat_node(state: AgentState):
    """mengelola chattingan umum"""
    messages = state["messages"]
    system_msg = SystemMessage(
        content="Kamu adalah Senior Product Strategist Agent yang cerdas."
    )

    response = llm.invoke([system_msg] + messages)

    return {"messages": messages + [response]}

# routing classification logic
def classification_logic(state: AgentState) -> Literal["strategic_data", "general_chat"]:
    """Memutuskan apakah perlu riset atau cuma ngobrol"""
    messages = state["messages"]
    last_message = messages[-1].content

    # cek keyword pesan sederhana untuk hemat API
    keywords = ["analisis", "riset", "strategi", "kompetitor", "pasar", "fitur", "ide"]
    if any(k in last_message.lower() for k in keywords):
        return "research_data"
    
    # prompt system untuk 
    prompt = (
        f"Klasifikasikan pesan ini: '{last_message}'. "
        "Apakah user meminta analisis/data produk (RESEARCH) atau hanya sapaan/obrolan (CHAT)? "
        "Jawab satu kata: RESEARCH atau CHAT."
    )

    # invoke
    response = llm.invoke([SystemMessage(content=prompt)] + messages)

    # cek jawaban
    if "RESEARCH" in response.content.strip().upper():
        return "research_data"
    else:
        return "general_chat"
    
# workflow logic
workflow = StateGraph(AgentState)

# workflow logic
workflow.add_node("research_data", research_data_node)
workflow.add_node("strategic_data", strategic_data_node)
workflow.add_node("general_chat", general_chat_node)

# set workflow entry point
workflow.set_conditional_entry_point(
    classification_logic,
    {
        "research_data": "research_data",
        "general_chat": "general_chat"
    }
)

workflow.add_edge("research_data", "strategic_data")

workflow.add_edge("strategic_data", END)
workflow.add_edge("general_chat", END)

product_agent_graph = workflow.compile()
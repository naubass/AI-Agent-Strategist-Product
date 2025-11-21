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
    file_content: str

# function to research data
def research_data_node(state: AgentState):
    """Function untuk research data dengan query pintar"""
    messages = state["messages"]
    last_message = messages[-1].content
    print(f"🕵️ [Research] Input User: {last_message}")

    # LOGIC PINTAR: Deteksi apakah ini perbandingan?
    # Jika ada kata 'vs', 'lawan', 'banding', atau 'kompetitor'
    keywords_banding = ["vs", "lawan", "banding", "kompetitor", "beda"]
    
    if any(k in last_message.lower() for k in keywords_banding):
        # Tambahkan keyword sakti untuk perbandingan
        query = f"{last_message} comparison market share features pros cons 2025 vs"
        print(f"🔎 Mode: COMPARISON SEARCH -> {query}")
    else:
        # Search biasa
        query = f"{last_message} market analysis trends statistics 2025"
        print(f"🔎 Mode: GENERAL SEARCH -> {query}")

    try:
        search_result = search.run(query)
    except Exception as e:
        search_result = f"Error searching: {e}"

    state["research_data"] = search_result
    return state

# function strategic data
def strategic_data_node(state: AgentState):
    """ Otak utama untuk menentukan strategi berdasarkan data yang diperoleh dan intruksi yg diberikan"""
    # ambil data dari state
    messages = state["messages"]
    research_data = state.get("research_data", "Tidak ada data riset")
    file_content = state.get("file_content", "Tidak ada konten file")

    print(f"🧠 [Strategist] Data Riset: {len(research_data)} chars")
    print(f"📂 [Strategist] Data File: {len(file_content)} chars")

    # tampilkan state research
    print(f"Data riset: {research_data}")

    system_prompt = """
    Peran: Senior Product Strategist.
    Tugas: Analisis data strategis dari Riset Pasar 2025 dan Data User.
    
    SUMBER DATA:
    1. DATA RISET INTERNET (Eksternal):
    {research_data}
    
    2. DATA FILE USER (Internal - PDF/Excel):
    {file_data}
    
    INSTRUKSI LOGIKA (PENTING):
    - Jika data berisi DUA kompetitor (misal A vs B), bagian "Insight" WAJIB membandingkan keduanya secara Head-to-Head (Market Share, Harga, atau Fitur).
    - Jika ada DATA FILE USER, jadikan itu prioritas utama untuk dianalisis, lalu validasi dengan data riset internet.
    - Jika data hanya SATU produk, fokus pada tren pasarnya.
    
    Instruksi Output (WAJIB Ikuti Format Ini):
    
    📈 **Insight Analisa Data:**
    - [Insight 1: Perbandingan Head-to-Head / Temuan Utama dari File]
    - [Insight 2: Tren Pasar Terkini 2025]

    📊 **Analisis SWOT:**
    - 💪 **Strengths:** [Kekuatan Utama]
    - ⚠️ **Weaknesses:** [Kelemahan / Pain Point User]
    - 🌟 **Opportunities:** [Peluang Bisnis / Celah Pasar]
    - ⚡ **Threats:** [Ancaman Kompetitor / Regulasi]

    🚀 **Rekomendasi Strategis:**
    - [Strategi Konkret 1]
    - [Strategi Konkret 2]

    ATURAN FORMATTING (ANTI-ERROR TELEGRAM):
    1. JANGAN gunakan simbol underscore (_) sama sekali. Ganti dengan spasi.
    2. Gunakan strip (-) untuk bullet points. JANGAN pakai bintang (*).
    3. Pastikan setiap tanda bintang ganda (**) untuk bold selalu ditutup rapat.
    4. Jawab SINGKAT & PADAT (Maksimal 2 poin per bagian).
    """

    system_message = SystemMessage(
        content=system_prompt.format(
            research_data=research_data if research_data else "Tidak ada data riset internet.",
            file_data=file_content if file_content else "Tidak ada file user diupload."
        )
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
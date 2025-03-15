import React, { useState, useEffect, useRef } from "react";
import { AppBar, Toolbar, Typography, TextField, IconButton, Paper, Container, Box, CircularProgress, Fab } from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import ChatBubbleOutlineIcon from "@mui/icons-material/ChatBubbleOutline";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown"; 

function App() {
    const [messages, setMessages] = useState([]);
    const [query, setQuery] = useState("");
    const [loading, setLoading] = useState(false);
    const [showScrollButton, setShowScrollButton] = useState(false);
    const inputRef = useRef(null);
    const chatContainerRef = useRef(null);

    const emptyState = messages.length === 0;

    const handleSend = async () => {
        if (!query.trim()) return;

        setLoading(true);
        const userMessage = { sender: "user", text: query };
        setMessages((prev) => [...prev, userMessage]);
        setQuery("");

        try {
            const res = await fetch(`http://localhost:8000/chat`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ query: query }),
            });

            const data = await res.json();
            const botMessage = { sender: "bot", text: data.ai_response };
            setMessages((prev) => [...prev, botMessage]);
        } catch (error) {
            console.log(error);
            setMessages((prev) => [...prev, { sender: "bot", text: "Error fetching response." }]);
        }
        setLoading(false);
    };

    useEffect(() => {
        inputRef.current?.focus();
    }, []);

    const handleScroll = () => {
        if (chatContainerRef.current) {
            const { scrollTop, scrollHeight, clientHeight } = chatContainerRef.current;
            setShowScrollButton(scrollHeight - scrollTop > clientHeight + 100); 
        }
    };

    const scrollToBottom = () => {
        chatContainerRef.current?.scrollTo({ top: chatContainerRef.current.scrollHeight, behavior: "smooth" });
        setShowScrollButton(false);
    };

    return (
        <Container maxWidth="md">
            <AppBar position="static" style={{ background: "#ffffff", color: "#000" }}>
                <Toolbar>
                    <ChatBubbleOutlineIcon style={{ marginRight: 10 }} />
                    <Typography variant="h6">Personal AI Chatbot</Typography>
                </Toolbar>
            </AppBar>

            <Paper elevation={3} 
                sx={{
                    height: "76vh",
                    marginTop: 2,
                    display: "flex",
                    flexDirection: "column",
                    position: "relative",
                    padding: 2
                }}
            >
                {emptyState ? (
                    <Box sx={{ textAlign: "center", marginTop: "30%", color: "#aaa" }}>
                        <Typography variant="h5">Ask me anything regarding your personal life</Typography>
                    </Box>
                ) : (
                    <Box 
                        ref={chatContainerRef}
                        sx={{
                            flexGrow: 1,
                            overflowY: "auto",
                            padding: "15px",
                            maxHeight: "65vh"  // Ensure scrolling when content exceeds this height
                        }}
                        onScroll={handleScroll}
                    >
                        {messages.map((msg, index) => (
                            <Box
                                key={index}
                                sx={{
                                    display: "flex",
                                    justifyContent: msg.sender === "user" ? "flex-end" : "flex-start",
                                    marginBottom: 1,
                                }}
                            >
                                <Paper
                                    sx={{
                                        padding: "10px 15px",
                                        borderRadius: "12px",
                                        backgroundColor: msg.sender === "user" ? "#0078FF" : "#F1F1F1",
                                        color: msg.sender === "user" ? "#fff" : "#000",
                                        maxWidth: "75%",
                                        wordWrap: "break-word",
                                        overflowWrap: "break-word",
                                        whiteSpace: "pre-wrap"
                                    }}
                                >
                                    {msg.text}
                                </Paper>
                            </Box>
                        ))}
                        {loading && (
                            <Box sx={{ textAlign: "center", padding: 2 }}>
                                <CircularProgress size={24} />
                            </Box>
                        )}
                    </Box>
                )}

                {showScrollButton && (
                    <Fab 
                        color="primary" 
                        size="small" 
                        onClick={scrollToBottom} 
                        sx={{ position: "absolute", bottom: 20, right: 20 }}
                    >
                        <KeyboardArrowDownIcon />
                    </Fab>
                )}
            </Paper>

            <Box sx={{ display: "flex", marginTop: 2 }}>
                <TextField
                    fullWidth
                    label="Ask anything..."
                    variant="outlined"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSend()}
                    inputRef={inputRef}
                />
                <IconButton color="primary" onClick={handleSend} disabled={loading}>
                    <SendIcon />
                </IconButton>
            </Box>
        </Container>
    );
}

export default App;

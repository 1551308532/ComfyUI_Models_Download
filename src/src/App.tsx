import React, { useState, useEffect } from 'react';
import {
    ThemeProvider, createTheme, CssBaseline, Grid, Box, Typography,
    AppBar, Toolbar, Button
} from '@mui/material';
import { produce } from 'immer';
import { v4 as uuidv4 } from 'uuid';
import TagList from './components/TagList';
import SchemeList from './components/SchemeList';
import FileTreeView from './components/FileTreeView';
import AddLinkModal from './components/AddLinkModal';
import FolderExplorerModal from './components/FolderExplorerModal';
import apiClient from './api';

const darkTheme = createTheme({
    palette: {
        mode: 'dark',
        primary: { main: '#90caf9' },
        secondary: { main: '#f48fb1' },
        background: { default: '#121212', paper: '#1e1e1e' },
    },
});

interface Config {
    tags: any;
    schemes: any;
    settings: any;
}

const App: React.FC = () => {
    const [config, setConfig] = useState<Config | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [selectedTag, setSelectedTag] = useState<string | null>(null);
    const [selectedScheme, setSelectedScheme] = useState<string | null>(null);

    // Modal States
    const [addLinkOpen, setAddLinkOpen] = useState(false);
    const [folderExplorerOpen, setFolderExplorerOpen] = useState(false);
    const [folderData, setFolderData] = useState<any>(null);
    const [loading, setLoading] = useState(false);

    const fetchConfig = () => {
        setLoading(true);
        apiClient.get('/config')
            .then(response => {
                setConfig(response.data);
                if (!selectedTag && !selectedScheme && Object.keys(response.data.tags).length > 0) {
                    setSelectedTag(Object.keys(response.data.tags)[0]);
                }
            })
            .catch(err => {
                console.error("Failed to fetch config:", err);
                setError("Could not connect to the backend. Please ensure it is running.");
            })
            .finally(() => setLoading(false));
    };

    useEffect(() => { fetchConfig(); }, []);

    const handleSelectTag = (tagName: string) => { setSelectedTag(tagName); setSelectedScheme(null); };
    const handleSelectScheme = (schemeName: string) => { setSelectedScheme(schemeName); setSelectedTag(null); };

    const handleConfigChange = (newConfig: Config) => {
        apiClient.post('/config', { data: newConfig })
            .then(() => fetchConfig())
            .catch(err => console.error("Failed to save config:", err));
    };

    const handleAddLink = (url: string) => {
        if (!selectedTag) {
            alert("Please select a tag first!");
            return;
        }
        setLoading(true);
        apiClient.post('/inspect-link', { url })
            .then(response => {
                const { type, details, contents } = response.data;
                if (type === 'file') {
                    const newConfig = produce(config!, (draft) => {
                        draft.tags[selectedTag!].push({ uuid: uuidv4(), ...details });
                    });
                    handleConfigChange(newConfig);
                    setAddLinkOpen(false);
                } else {
                    setFolderData({ details, contents });
                    setFolderExplorerOpen(true);
                    setAddLinkOpen(false);
                }
            })
            .catch(err => alert(`Error inspecting link: ${err.response?.data?.detail || err.message}`))
            .finally(() => setLoading(false));
    };

    const handleFolderConfirm = (selectedItems: any[], addAsSingleDir: boolean) => {
        if (!selectedTag) return;

        const newConfig = produce(config!, (draft) => {
            const tagItems = draft.tags[selectedTag!];
            if (addAsSingleDir) {
                tagItems.push({ uuid: uuidv4(), ...folderData.details });
            } else {
                selectedItems.forEach(item => {
                    tagItems.push({
                        uuid: uuidv4(),
                        repo_id: folderData.details.repo_id,
                        path: item.path,
                        type: item.type,
                    });
                });
            }
        });
        handleConfigChange(newConfig);
        setFolderExplorerOpen(false);
    };

    if (error) return <Box sx={{ p: 4, color: 'red' }}>Error: {error}</Box>;
    if (!config) return <Box sx={{ p: 4 }}>Loading configuration...</Box>;

    return (
        <ThemeProvider theme={darkTheme}>
            <CssBaseline />
            <Box sx={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
                <AppBar position="static" color="default" elevation={1}>
                    <Toolbar variant="dense">
                        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>HF Download Manager</Typography>
                        <Button color="primary" variant="outlined" onClick={() => setAddLinkOpen(true)} disabled={!selectedTag}>Add Link to Tag</Button>
                        <Button color="secondary" variant="outlined" sx={{ ml: 2 }}>Generate Script</Button>
                    </Toolbar>
                </AppBar>
                <Grid container sx={{ flexGrow: 1, overflow: 'hidden' }}>
                    <Grid item xs={3} sx={{ display: 'flex', flexDirection: 'column', height: '100%', borderRight: '1px solid #424242' }}>
                        <Box sx={{ flex: 1, overflowY: 'auto', p: 1 }}><TagList tags={Object.keys(config.tags)} selectedTag={selectedTag} onSelectTag={handleSelectTag} onDataChange={fetchConfig} /></Box>
                        <Box sx={{ flex: 1, overflowY: 'auto', borderTop: '1px solid #424242', p: 1 }}><SchemeList schemes={Object.keys(config.schemes)} selectedScheme={selectedScheme} onSelectScheme={handleSelectScheme} onDataChange={fetchConfig} /></Box>
                    </Grid>
                    <Grid item xs={9} sx={{ height: '100%', overflowY: 'auto', p: 2 }}>
                        <FileTreeView key={selectedTag || selectedScheme} config={config} selectedItemKey={selectedTag ? 'tags' : 'schemes'} selectedItemName={selectedTag || selectedScheme || ''} onConfigChange={handleConfigChange} />
                    </Grid>
                </Grid>
                <AddLinkModal open={addLinkOpen} onClose={() => setAddLinkOpen(false)} onAddLink={handleAddLink} loading={loading} />
                <FolderExplorerModal open={folderExplorerOpen} onClose={() => setFolderExplorerOpen(false)} folderData={folderData} onConfirm={handleFolderConfirm} />
            </Box>
        </ThemeProvider>
    );
};

export default App;

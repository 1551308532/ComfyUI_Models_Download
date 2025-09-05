import React, { useState } from 'react';
import {
    Dialog, DialogTitle, DialogContent, TextField, DialogActions, Button, Box, CircularProgress
} from '@mui/material';

interface AddLinkModalProps {
    open: boolean;
    onClose: () => void;
    onAddLink: (url: string) => void;
    loading: boolean;
}

const AddLinkModal: React.FC<AddLinkModalProps> = ({ open, onClose, onAddLink, loading }) => {
    const [url, setUrl] = useState('');

    const handleAdd = () => {
        if (url.trim()) {
            onAddLink(url.trim());
        }
    };

    return (
        <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
            <DialogTitle>Add HuggingFace Link</DialogTitle>
            <DialogContent>
                <TextField
                    autoFocus
                    margin="dense"
                    id="url"
                    label="HuggingFace URL"
                    type="text"
                    fullWidth
                    variant="outlined"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleAdd()}
                    placeholder="e.g., https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0"
                />
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose} disabled={loading}>Cancel</Button>
                <Button onClick={handleAdd} variant="contained" disabled={loading}>
                    {loading ? <CircularProgress size={24} /> : 'Inspect Link'}
                </Button>
            </DialogActions>
        </Dialog>
    );
};

export default AddLinkModal;

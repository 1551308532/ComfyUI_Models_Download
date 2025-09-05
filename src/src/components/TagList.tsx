import React, { useState } from 'react';
import {
    Box, Typography, List, ListItem, ListItemButton, ListItemText,
    IconButton, Dialog, DialogTitle, DialogContent, TextField, DialogActions, Button
} from '@mui/material';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import DeleteIcon from '@mui/icons-material/Delete';
import apiClient from '../api';

interface TagListProps {
    tags: string[];
    selectedTag: string | null;
    onSelectTag: (tagName: string) => void;
    onDataChange: () => void;
}

const TagList: React.FC<TagListProps> = ({ tags, selectedTag, onSelectTag, onDataChange }) => {
    const [open, setOpen] = useState(false);
    const [newTagName, setNewTagName] = useState('');

    const handleAddTag = () => {
        if (newTagName.trim()) {
            apiClient.post('/tags', { name: newTagName.trim() })
                .then(() => {
                    onDataChange();
                    setOpen(false);
                    setNewTagName('');
                })
                .catch(err => console.error("Failed to add tag:", err));
        }
    };

    const handleDeleteTag = (tagName: string, event: React.MouseEvent) => {
        event.stopPropagation(); // Prevent the list item click from firing
        if (window.confirm(`Are you sure you want to delete the tag "${tagName}"?`)) {
            apiClient.delete(`/tags/${tagName}`)
                .then(() => {
                    onDataChange();
                })
                .catch(err => console.error("Failed to delete tag:", err));
        }
    };

    return (
        <Box sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <Typography variant="h6" sx={{ flexGrow: 1 }}>
                    Tags
                </Typography>
                <IconButton onClick={() => setOpen(true)} color="primary">
                    <AddCircleOutlineIcon />
                </IconButton>
            </Box>
            <List dense>
                {tags.map(tag => (
                    <ListItem
                        key={tag}
                        disablePadding
                        secondaryAction={
                            <IconButton edge="end" aria-label="delete" onClick={(e) => handleDeleteTag(tag, e)}>
                                <DeleteIcon fontSize="small" />
                            </IconButton>
                        }
                    >
                        <ListItemButton
                            selected={selectedTag === tag}
                            onClick={() => onSelectTag(tag)}
                        >
                            <ListItemText primary={tag} />
                        </ListItemButton>
                    </ListItem>
                ))}
            </List>

            {/* Add Tag Dialog */}
            <Dialog open={open} onClose={() => setOpen(false)}>
                <DialogTitle>Add New Tag</DialogTitle>
                <DialogContent>
                    <TextField
                        autoFocus
                        margin="dense"
                        id="name"
                        label="Tag Name"
                        type="text"
                        fullWidth
                        variant="standard"
                        value={newTagName}
                        onChange={(e) => setNewTagName(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleAddTag()}
                    />
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setOpen(false)}>Cancel</Button>
                    <Button onClick={handleAddTag}>Add</Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
};

export default TagList;

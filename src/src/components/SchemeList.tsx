import React, { useState } from 'react';
import {
    Box, Typography, List, ListItem, ListItemButton, ListItemText,
    IconButton, Dialog, DialogTitle, DialogContent, TextField, DialogActions, Button
} from '@mui/material';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import DeleteIcon from '@mui/icons-material/Delete';
import apiClient from '../api';

interface SchemeListProps {
    schemes: string[];
    selectedScheme: string | null;
    onSelectScheme: (schemeName: string) => void;
    onDataChange: () => void;
}

const SchemeList: React.FC<SchemeListProps> = ({ schemes, selectedScheme, onSelectScheme, onDataChange }) => {
    const [open, setOpen] = useState(false);
    const [newSchemeName, setNewSchemeName] = useState('');

    const handleAddScheme = () => {
        if (newSchemeName.trim()) {
            apiClient.post('/schemes', { name: newSchemeName.trim() })
                .then(() => {
                    onDataChange();
                    setOpen(false);
                    setNewSchemeName('');
                })
                .catch(err => console.error("Failed to add scheme:", err));
        }
    };

    const handleDeleteScheme = (schemeName: string, event: React.MouseEvent) => {
        event.stopPropagation();
        if (window.confirm(`Are you sure you want to delete the scheme "${schemeName}"?`)) {
            apiClient.delete(`/schemes/${schemeName}`)
                .then(() => {
                    onDataChange();
                })
                .catch(err => console.error("Failed to delete scheme:", err));
        }
    };

    return (
        <Box sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <Typography variant="h6" sx={{ flexGrow: 1 }}>
                    Schemes
                </Typography>
                <IconButton onClick={() => setOpen(true)} color="primary">
                    <AddCircleOutlineIcon />
                </IconButton>
            </Box>
            <List dense>
                {schemes.map(scheme => (
                    <ListItem
                        key={scheme}
                        disablePadding
                        secondaryAction={
                            <IconButton edge="end" aria-label="delete" onClick={(e) => handleDeleteScheme(scheme, e)}>
                                <DeleteIcon fontSize="small" />
                            </IconButton>
                        }
                    >
                        <ListItemButton
                            selected={selectedScheme === scheme}
                            onClick={() => onSelectScheme(scheme)}
                        >
                            <ListItemText primary={scheme} />
                        </ListItemButton>
                    </ListItem>
                ))}
            </List>

            {/* Add Scheme Dialog */}
            <Dialog open={open} onClose={() => setOpen(false)}>
                <DialogTitle>Add New Scheme</DialogTitle>
                <DialogContent>
                    <TextField
                        autoFocus
                        margin="dense"
                        id="name"
                        label="Scheme Name"
                        type="text"
                        fullWidth
                        variant="standard"
                        value={newSchemeName}
                        onChange={(e) => setNewSchemeName(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleAddScheme()}
                    />
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setOpen(false)}>Cancel</Button>
                    <Button onClick={handleAddScheme}>Add</Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
};

export default SchemeList;

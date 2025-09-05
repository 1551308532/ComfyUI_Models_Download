import React, { useState, useEffect } from 'react';
import {
    Dialog, DialogTitle, DialogContent, DialogActions, Button, Box, List, ListItem,
    Checkbox, ListItemText, Typography, FormControlLabel
} from '@mui/material';

interface FolderExplorerModalProps {
    open: boolean;
    onClose: () => void;
    folderData: any;
    onConfirm: (selectedItems: any[], addAsSingleDir: boolean) => void;
}

const FolderExplorerModal: React.FC<FolderExplorerModalProps> = ({ open, onClose, folderData, onConfirm }) => {
    const [selected, setSelected] = useState<string[]>([]);
    const [addAsSingleDir, setAddAsSingleDir] = useState(false);

    useEffect(() => {
        // Reset selection when modal opens
        if (open) {
            setSelected([]);
            setAddAsSingleDir(false);
        }
    }, [open]);

    const handleToggle = (value: string) => () => {
        const currentIndex = selected.indexOf(value);
        const newSelected = [...selected];

        if (currentIndex === -1) {
            newSelected.push(value);
        } else {
            newSelected.splice(currentIndex, 1);
        }
        setSelected(newSelected);
    };

    const handleConfirm = () => {
        const selectedItems = folderData.contents.filter((item: any) => selected.includes(item.path));
        onConfirm(selectedItems, addAsSingleDir);
    };

    return (
        <Dialog open={open} onClose={onClose} fullWidth maxWidth="md">
            <DialogTitle>Select Contents from "{folderData?.details?.repo_id}"</DialogTitle>
            <DialogContent>
                <Typography variant="caption" display="block" gutterBottom>
                    Path: {folderData?.details?.path}
                </Typography>
                <Box border={1} borderColor="grey.700" borderRadius={1} sx={{ height: 400, overflow: 'auto' }}>
                    <List dense>
                        {folderData?.contents?.map((item: any) => (
                            <ListItem key={item.path} dense disablePadding>
                                <Checkbox
                                    edge="start"
                                    checked={selected.indexOf(item.path) !== -1}
                                    tabIndex={-1}
                                    disableRipple
                                    onChange={handleToggle(item.path)}
                                    disabled={addAsSingleDir}
                                />
                                <ListItemText primary={item.path} secondary={item.type} />
                            </ListItem>
                        ))}
                    </List>
                </Box>
                <FormControlLabel
                    control={<Checkbox checked={addAsSingleDir} onChange={(e) => setAddAsSingleDir(e.target.checked)} />}
                    label="Add as a single directory (folder/*)"
                    sx={{ mt: 2 }}
                />
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose}>Cancel</Button>
                <Button onClick={handleConfirm} variant="contained">Add Selected</Button>
            </DialogActions>
        </Dialog>
    );
};

export default FolderExplorerModal;

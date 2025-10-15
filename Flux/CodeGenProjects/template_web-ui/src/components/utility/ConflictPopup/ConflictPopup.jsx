import React from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
// import Paper from '@mui/material/Paper';
import Box from '@mui/material/Box';
import Warning from '@mui/icons-material/Warning';

const ConflictPopup = ({ 
    open, 
    onClose, 
    onDiscardChanges, 
    onOverwriteChanges, 
    conflicts = [],
    title = "Conflict Detected" 
}) => {
    return (
        <Dialog
            open={open}
            onClose={onClose}
            maxWidth="md"
            fullWidth
            PaperProps={{
                sx: {
                    borderRadius: 2,
                    boxShadow: 3
                }
            }}
        >
            <DialogTitle sx={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: 1,
                backgroundColor: '#fff3e0',
                color: '#e65100'
            }}>
                <Warning color="warning" />
                {title}
            </DialogTitle>
            
            <DialogContent sx={{ pt: 2 }}>
                <Typography variant="body1" gutterBottom>
                    The data has been modified by another user/server update while you were editing. 
                    Please review the conflicts below and choose how to proceed:
                </Typography>
                
                <Box sx={{ mt: 2 }}>
                    <TableContainer variant="outlined">
                        <Table size="small">
                            <TableHead>
                                <TableRow sx={{ backgroundColor: '#cc3e3e' }}>
                                    <TableCell><strong>Field</strong></TableCell>
                                    <TableCell><strong>Your Value</strong></TableCell>
                                    <TableCell><strong>Server Value</strong></TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {conflicts.map((conflict, index) => (
                                    <TableRow key={index}>
                                        <TableCell>{conflict.field}</TableCell>
                                        <TableCell sx={{ color: '#1976d2' }}>
                                            {conflict.yourValue?.toString() || 'N/A'}
                                        </TableCell>
                                        <TableCell sx={{ color: '#d32f2f' }}>
                                            {conflict.serverValue?.toString() || 'N/A'}
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </TableContainer>
                </Box>
            </DialogContent>
            
            <DialogActions sx={{ p: 2, gap: 1 }}>
                <Button 
                    onClick={onDiscardChanges}
                    variant="contained"
                    color="error"
                >
                    Discard My Changes
                </Button>
                <Button 
                    onClick={onOverwriteChanges}
                    variant="contained"
                    color="primary"
                >
                    Overwrite with My Changes
                </Button>
            </DialogActions>
        </Dialog>
    );
};

export default ConflictPopup; 
import { Alert, Typography, Box } from '@mui/material';
import { ErrorBoundary as Boundary } from 'react-error-boundary'
import { ErrorOutline } from '@mui/icons-material';

function ErrorFallback({ error, resetErrorBoundary }) {
    return (
        <Box sx={{ padding: 10 }}>
            <Typography variant='h4'><ErrorOutline color='error' />Something went wrong</Typography>
            <Alert severity='error'>
                <Typography variant='subtitle1'>
                    <div><pre>{error.message}</pre></div>
                </Typography>
                <Typography variant='body2'>
                    <div><pre>{error.stack}</pre></div>
                </Typography>
            </Alert>
        </Box>
    )
}

const ErrorBoundary = (props) => (
    <Boundary
        FallbackComponent={ErrorFallback}
        onReset={() => {
            // reset the state of your app so the error doesn't happen again
        }}
    >
        {props.children}
    </Boundary>
)

export default ErrorBoundary;
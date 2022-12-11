import React from 'react';
import { Autocomplete, Box, TextField, Button, Divider, List, ListItem, ListItemButton, ListItemText, Chip, Badge } from '@mui/material';
import { makeStyles } from '@mui/styles';
import WidgetContainer from './WidgetContainer';
import { Download, Delete } from '@mui/icons-material';
import PropTypes from 'prop-types';
import Icon from './Icon';
import _ from 'lodash';
import { ColorTypes, DB_ID } from '../constants';
import Alert from './Alert';

const useStyles = makeStyles({
    autocompleteDropdownContainer: {
        display: 'flex',
        margin: '10px 0'
    },
    autocomplete: {
        flex: 1,
        background: 'white'
    },
    button: {
        margin: '0 5px !important'
    },
    listItem: {
        padding: '0 10px'
    },
    badge: {
        margin: '0 10px'
    }
})

const AbbreviatedFilterWidget = (props) => {

    const classes = useStyles();

    return (
        <WidgetContainer
            title={props.headerProps.title}
            mode={props.headerProps.mode}
            menu={props.headerProps.menu}
            onChangeMode={props.headerProps.onChangeMode}
            onSave={props.headerProps.onSave}
            onReload={props.headerProps.onReload}
        >
            <Box className={classes.autocompleteDropdownContainer}>
                <Autocomplete
                    className={classes.autocomplete}
                    options={props.options}
                    getOptionLabel={(option) => option}
                    disableClearable
                    variant='outlined'
                    size='small'
                    value={props.searchValue ? props.searchValue : null}
                    onChange={props.onChange}
                    renderInput={(params) => <TextField {...params} label={props.bufferedLabel} />}
                />
                <Button className={classes.button} variant='contained' disableElevation disabled={props.searchValue ? false : true} onClick={props.onLoad}>
                    <Download fontSize='small' />
                </Button>
            </Box>
            <Divider textAlign='left'><Chip label={props.loadedLabel} /></Divider>
            <List>
                {props.items && props.items.map((item, i) => {
                    let index = props.abbreviated.split('-').length - 1;
                    let id = item.split('-')[index] * 1;
                    let metadata = props.itemsMetadata.filter(metadata => _.get(metadata, DB_ID) === id)[0];
                    let alertCount = 0;
                    let bubbleColor = ColorTypes.UNSPECIFIED;
                    if (_.get(metadata, props.alertBubbleSource)) {
                        alertCount = _.get(metadata, props.alertBubbleSource).length;
                    }
                    if (alertCount > 0) {
                        let xpath = props.alertBubbleColorSource.substring(0, props.alertBubbleColorSource.lastIndexOf('.')) + '[0].' + props.alertBubbleColorSource.split('.').pop();
                        bubbleColor = ColorTypes[_.get(metadata, xpath).split('_')[1]]
                    }
                    return (
                        <ListItem key={i} className={classes.listItem} selected={props.selected === id} disablePadding>
                            {alertCount > 0 && <Badge className={classes.badge} badgeContent={alertCount} color={bubbleColor} />}
                            <ListItemButton onClick={() => props.onSelect(id)}>
                                <ListItemText>
                                    {item}
                                </ListItemText>
                            </ListItemButton>
                            <Icon title='Unload' onClick={() => props.onUnload(item)}>
                                <Delete fontSize='small' />
                            </Icon>
                        </ListItem>
                    )
                })}
            </List>
            {props.error && <Alert open={props.error ? true : false} onClose={props.onResetError} severity='error'>{props.error}</Alert>}
        </WidgetContainer>
    )
}

AbbreviatedFilterWidget.propTypes = {
    headerProps: PropTypes.object.isRequired,
    options: PropTypes.array,
    searchValue: PropTypes.string,
    onChange: PropTypes.func,
    bufferedLabel: PropTypes.string,
    onLoad: PropTypes.func,
    loadedLabel: PropTypes.string,
    selected: PropTypes.number,
    onSelect: PropTypes.func,
    onUnload: PropTypes.func
}

export default AbbreviatedFilterWidget;
'''
        Created on 2/01/2014

        @author: graemeg
        '''

def message_post(self, cr, uid, thread_id, body='', subject=None, type='notification',
                        subtype=None, parent_id=False, attachments=None, context=None,
                        content_subtype='html', **kwargs):
        """ Post a new message in an existing thread, returning the new
            mail.message ID.
        :param int thread_id: thread ID to post into, or list with one ID;
            if False/0, mail.message model will also be set as False
        :param str body: body of the message, usually raw HTML that will
            be sanitized
        :param str type: see mail_message.type field
        :param str content_subtype:: if plaintext: convert body into html
        :param int parent_id: handle reply to a previous message by adding the
            parent partners to the message in case of private discussion
        :param tuple(str,str) attachments or list id: list of attachment tuples in the form
            ``(name,content)``, where content is NOT base64 encoded

        Extra keyword arguments will be used as default column values for the
        new mail.message record. Special cases:
            - attachment_ids: supposed not attached to any document; attach them
                to the related document. Should only be set by Chatter.
        :return int: ID of newly created mail.message
    """
    if context is None:
        context = {}
    if attachments is None:
        attachments = {}
    mail_message = self.pool.get('mail.message')
    ir_attachment = self.pool.get('ir.attachment')

    assert (not thread_id) or \
            isinstance(thread_id, (int, long)) or \
            (isinstance(thread_id, (list, tuple)) and len(thread_id) == 1), \
            "Invalid thread_id; should be 0, False, an ID or a list with one ID"
    if isinstance(thread_id, (list, tuple)):
        thread_id = thread_id[0]

    # if we're processing a message directly coming from the gateway, the destination model was
    # set in the context.
    model = False
    if thread_id:
        model = context.get('thread_model', self._name) if self._name == 'mail.thread' else self._name
        if model != self._name:
            del context['thread_model']
            return self.pool.get(model).message_post(cr, uid, thread_id, body=body, subject=subject, type=type, subtype=subtype, parent_id=parent_id, attachments=attachments, context=context, content_subtype=content_subtype, **kwargs)

    # 0: Parse email-from, try to find a better author_id based on document's followers for incoming emails
    email_from = kwargs.get('email_from')
    if email_from and thread_id and type == 'email' and kwargs.get('author_id'):
        email_list = tools.email_split(email_from)
        doc = self.browse(cr, uid, thread_id, context=context)
        if email_list and doc:
            author_ids = self.pool.get('res.partner').search(cr, uid, [
                                    ('email', 'ilike', email_list[0]),
                                    ('id', 'in', [f.id for f in doc.message_follower_ids])
                                ], limit=1, context=context)
            if author_ids:
                kwargs['author_id'] = author_ids[0]
    author_id = kwargs.get('author_id')
    if author_id is None:  # keep False values
        author_id = self.pool.get('mail.message')._get_default_author(cr, uid, context=context)

    # 1: Handle content subtype: if plaintext, converto into HTML
    if content_subtype == 'plaintext':
        body = tools.plaintext2html(body)

    # 2: Private message: add recipients (recipients and author of parent message) - current author
    #   + legacy-code management (! we manage only 4 and 6 commands)
    partner_ids = set()
    kwargs_partner_ids = kwargs.pop('partner_ids', [])
    for partner_id in kwargs_partner_ids:
        if isinstance(partner_id, (list, tuple)) and partner_id[0] == 4 and len(partner_id) == 2:
            partner_ids.add(partner_id[1])
        if isinstance(partner_id, (list, tuple)) and partner_id[0] == 6 and len(partner_id) == 3:
            partner_ids |= set(partner_id[2])
        elif isinstance(partner_id, (int, long)):
            partner_ids.add(partner_id)
        else:
            pass  # we do not manage anything else
    if parent_id and not model:
        parent_message = mail_message.browse(cr, uid, parent_id, context=context)
        private_followers = set([partner.id for partner in parent_message.partner_ids])
        if parent_message.author_id:
            private_followers.add(parent_message.author_id.id)
        private_followers -= set([author_id])
        partner_ids |= private_followers

    # 3. Attachments
    #   - HACK TDE FIXME: Chatter: attachments linked to the document (not done JS-side), load the message
    attachment_ids = kwargs.pop('attachment_ids', []) or []  # because we could receive None (some old code sends None)
    if attachment_ids:
        filtered_attachment_ids = ir_attachment.search(cr, SUPERUSER_ID, [
            ('res_model', '=', 'mail.compose.message'),
            ('res_id', '=', 0),
            ('create_uid', '=', uid),
            ('id', 'in', attachment_ids)], context=context)
        if filtered_attachment_ids:
            ir_attachment.write(cr, SUPERUSER_ID, filtered_attachment_ids, {'res_model': model, 'res_id': thread_id}, context=context)
    attachment_ids = [(4, id) for id in attachment_ids]
    # Handle attachments parameter, that is a dictionary of attachments
    for name, content in attachments:
        if isinstance(content, unicode):
            content = content.encode('utf-8')
        data_attach = {
            'name': name,
            'datas': base64.b64encode(str(content)),
            'datas_fname': name,
            'description': name,
            'res_model': model,
            'res_id': thread_id,
        }
        attachment_ids.append((0, 0, data_attach))

    # 4: mail.message.subtype
    subtype_id = False
    if subtype:
        if '.' not in subtype:
            subtype = 'mail.%s' % subtype
        ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, *subtype.split('.'))
        subtype_id = ref and ref[1] or False

    # automatically subscribe recipients if asked to
    if context.get('mail_post_autofollow') and thread_id and partner_ids:
        partner_to_subscribe = partner_ids
        if context.get('mail_post_autofollow_partner_ids'):
            partner_to_subscribe = filter(lambda item: item in context.get('mail_post_autofollow_partner_ids'), partner_ids)
        self.message_subscribe(cr, uid, [thread_id], list(partner_to_subscribe), context=context)

    # _mail_flat_thread: automatically set free messages to the first posted message
    if self._mail_flat_thread and not parent_id and thread_id:
        message_ids = mail_message.search(cr, uid, ['&', ('res_id', '=', thread_id), ('model', '=', model)], context=context, order="id ASC", limit=1)
        parent_id = message_ids and message_ids[0] or False
    # we want to set a parent: force to set the parent_id to the oldest ancestor, to avoid having more than 1 level of thread
    elif parent_id:
        message_ids = mail_message.search(cr, SUPERUSER_ID, [('id', '=', parent_id), ('parent_id', '!=', False)], context=context)
        # avoid loops when finding ancestors
        processed_list = []
        if message_ids:
            message = mail_message.browse(cr, SUPERUSER_ID, message_ids[0], context=context)
            while (message.parent_id and message.parent_id.id not in processed_list):
                processed_list.append(message.parent_id.id)
                message = message.parent_id
            parent_id = message.id

    values = kwargs
    values.update({
        'author_id': author_id,
        'model': model,
        'res_id': thread_id or False,
        'body': body,
        'subject': subject or False,
        'type': type,
        'parent_id': parent_id,
        'attachment_ids': attachment_ids,
        'subtype_id': subtype_id,
        'partner_ids': [(4, pid) for pid in partner_ids],
    })

    # Avoid warnings about non-existing fields
    for x in ('from', 'to', 'cc'):
        values.pop(x, None)

    # Create and auto subscribe the author
    msg_id = mail_message.create(cr, uid, values, context=context)
    message = mail_message.browse(cr, uid, msg_id, context=context)
    if message.author_id and thread_id and type != 'notification' and not context.get('mail_create_nosubscribe'):
        self.message_subscribe(cr, uid, [thread_id], [message.author_id.id], context=context)
    return msg_id
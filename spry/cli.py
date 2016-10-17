import sys
import time

import click
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

from spry import api
from spry.utils import (
    BINARY_PREFIX, bytes_to_unit_pair, parse_kwargs, parse_speed_limit, seconds_to_eta_string
)


# TODO: support all
AUTH_MAP = {
    'basic': HTTPBasicAuth,
    'digest': HTTPDigestAuth,
    'oauth1': None,
    'kerberos': None,
    'ntlm': None
}

GLOBAL_CONTEXT_SETTINGS = {
    'max_content_width': 300
}


def get_password(ctx, param, value):
    username = ctx.params.get('username', None)
    if not value and username:
        value = click.prompt('Please enter password for {}'.format(username), hide_input=True)
    return value


@click.group(context_settings=GLOBAL_CONTEXT_SETTINGS)
@click.option('--parts', '-p', type=int, default=4, help='Number of simultaneous connections\nDefault: 4')
@click.option('--limit', '-l', type=(float, click.Choice(BINARY_PREFIX.keys())), default=(0.0, 'KiB'),
              metavar='NUMBER [{}]'.format('|'.join(BINARY_PREFIX.keys())),
              help='Speed limit per second\nDefault: None')
@click.option('--timeout', '-t', type=int, default=20, help='Number of seconds to wait on a disconnection\nDefault: 20')
@click.option('--silent', '-s', is_flag=True, help='Disables progress updates')
@click.option('--restart', is_flag=True)
def spry(restart, parts, limit, timeout, silent):
    pass


@spry.group(chain=True, short_help='Connect via HTTP(S)', context_settings=GLOBAL_CONTEXT_SETTINGS)
@click.option('--username', '-un')
@click.option('--password', '-pw', callback=get_password)
@click.option('--auth', type=click.Choice(('basic', 'digest', 'oauth1', 'kerberos', 'ntlm')),
              default='basic', help='Method of authentication')
@click.option('--secure/--insecure')
def http(username, password, auth, secure):
    pass


@http.command(context_settings=GLOBAL_CONTEXT_SETTINGS)
@click.pass_context
@click.option('--url', '-u', required=True, multiple=True)
@click.option('--path', '-p', required=True)
@click.option('--persist/--new', default=True)
def get(ctx, url, path, persist):
    general_params = ctx.parent.parent.params
    http_params = ctx.parent.params

    restart = general_params['restart']
    parts = general_params['parts']
    limit = general_params['limit']
    timeout = general_params['timeout']
    silent = general_params['silent']

    username = http_params['username']
    password = http_params['password']
    auth_type = http_params['auth']
    secure = http_params['secure']

    session = api.HTTPSession(concurrent=4, parts=parts, speed_limit=limit, timeout=timeout, restart=restart)
    session.limiter.promote()

    for u in url:
        session.get(
            url=u, path=path, parts=parts, speed_limit=limit, timeout=timeout, restart=restart,
            persist=persist, auth=AUTH_MAP[auth_type](username, password), verify=secure
        )

    show_progress(session, method='get', silent=silent)


@http.command(context_settings=GLOBAL_CONTEXT_SETTINGS)
def send():
    print('send')


@spry.group(short_help='Connect via SFTP')
def sftp():
    pass


@sftp.command(context_settings=GLOBAL_CONTEXT_SETTINGS)
def get():
    print('get')


@sftp.command(context_settings=GLOBAL_CONTEXT_SETTINGS)
def send():
    print('send')


def show_progress(session, method='get', silent=False):

    print('')

    if method == 'get':
        for file in session.unfinished:
            print('Getting {}'.format(file.remote_path))
    else:
        if not session.local_path:
            time.sleep(.5)
        print('\nSending {}\n'.format(session.local_path))

    print('\n')
    session.run()

    previous_output_length = 0
    final_update_needed = True if not silent else False

    while session.is_running or final_update_needed:
        time.sleep(.5)

        if not silent:

            # See if we finished since initial check; if so, end loop.
            if not session.is_running:
                final_update_needed = False

            bps, eta, total, size = session.tracker.get_progress()
            bps_value, bps_unit = bytes_to_unit_pair(bps)

            eta = seconds_to_eta_string(eta)

            s_value, s_unit = bytes_to_unit_pair(size)
            t_value, t_unit = bytes_to_unit_pair(total, s_unit if size else None)

            speed = 'Speed: {:.2f} {}/s'.format(bps_value, bps_unit)
            eta = 'ETA: {}'.format(eta)
            file_progress = 'File: {:.2f} {} / {:.2f} {}'.format(t_value, t_unit, s_value, s_unit)
            status = '{} <|> {} <|> {}'.format(speed, eta, file_progress)

            status_length = len(status)
            if status_length < previous_output_length:
                status += (previous_output_length - status_length) * ' '

            previous_output_length = len(status)

            s = '{}\r'.format(status)
            sys.stdout.write(s)
            sys.stdout.flush()

    #print('\n', session.finished, session.unfinished, session.errors, session.workers)
    print('\n\n')

    if method == 'get':
        for file in session.finished:
            print('Saved to {}'.format(file.local_path))
    else:
        print('\n\nSent to {}\n'.format(session.remote_path))

    print('\n')

    if not session.errors:
        print('Transfer successful')
    else:
        print('Error. Try again with --resume')

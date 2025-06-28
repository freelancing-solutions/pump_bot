import os
import logging
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from dotenv import load_dotenv
import threading
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager

# Custom Modules
from src.config import Config
from src.modules.solana_client import SolanaClient
from src.modules.pump_portal_client import PumpPortalClient
from src.modules.ai_client import AIClient
from src.modules.trade_manager import TradeManager
from src.modules.launch_manager import LaunchManager
from src.modules.social_media_manager import SocialMediaManager
from src.modules.db_manager import DBManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()


class AppManager:
    """Central application manager to handle all components and background tasks."""

    def __init__(self):
        self.app = None
        self.background_tasks = []
        self.websocket_task = None
        self.is_running = False

        # Initialize components
        self._init_components()

    def _init_components(self):
        """Initialize all application components."""
        try:
            # Core clients
            self.solana_client = SolanaClient(Config.SOLANA_RPC_URL)
            self.pump_portal_client = PumpPortalClient(Config.PUMPP_API_KEY)
            self.ai_client = AIClient(Config.OPENROUTER_API_KEY)
            self.db_manager = DBManager(Config.DATABASE_PATH)

            # Social media manager
            self.social_media_manager = SocialMediaManager(
                twitter_creds=self._get_twitter_creds(),
                telegram_token=Config.TELEGRAM_BOT_TOKEN,
                discord_token=Config.DISCORD_BOT_TOKEN
            )

            # Core managers
            self.trade_manager = TradeManager(
                solana_client=self.solana_client,
                pump_portal_client=self.pump_portal_client,
                db_manager=self.db_manager,
                ai_client=self.ai_client,
                social_media_manager=self.social_media_manager
            )

            self.launch_manager = LaunchManager(
                solana_client=self.solana_client,
                pump_portal_client=self.pump_portal_client,
                db_manager=self.db_manager,
                ai_client=self.ai_client,
                social_media_manager=self.social_media_manager
            )

            logger.info("All components initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise

    def _get_twitter_creds(self):
        """Get Twitter credentials from config."""
        return {
            'api_key': Config.TWITTER_API_KEY,
            'api_secret': Config.TWITTER_API_SECRET,
            'access_token': Config.TWITTER_ACCESS_TOKEN,
            'access_token_secret': Config.TWITTER_ACCESS_TOKEN_SECRET
        }

    async def start_websocket_listener(self):
        """Start the WebSocket listener for real-time trading data."""
        try:
            logger.info("Starting PumpPortal WebSocket listener...")
            await self.pump_portal_client.listen_for_trades(
                self.trade_manager.process_realtime_trade
            )
        except Exception as e:
            logger.error(f"WebSocket listener error: {e}")

    def start_background_tasks(self):
        """Start all background tasks."""
        if self.is_running:
            return

        self.is_running = True

        # Start WebSocket listener
        def websocket_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.start_websocket_listener())
            except Exception as e:
                logger.error(f"WebSocket thread error: {e}")
            finally:
                loop.close()

        self.websocket_task = threading.Thread(target=websocket_thread, daemon=True)
        self.websocket_task.start()

        # Add other background tasks here (monitoring, cleanup, etc.)
        self._start_monitoring_tasks()

        logger.info("Background tasks started")

    def _start_monitoring_tasks(self):
        """Start monitoring and maintenance tasks."""

        def monitoring_loop():
            while self.is_running:
                try:
                    # Update coin statuses
                    self._update_coin_statuses()
                    # Clean old data
                    self._cleanup_old_data()
                    # Health checks
                    self._perform_health_checks()

                    # Sleep for 60 seconds
                    threading.Event().wait(60)
                except Exception as e:
                    logger.error(f"Monitoring task error: {e}")

        monitor_thread = threading.Thread(target=monitoring_loop, daemon=True)
        monitor_thread.start()
        self.background_tasks.append(monitor_thread)

    def _update_coin_statuses(self):
        """Update status of active coins."""
        try:
            active_coins = self.db_manager.get_active_coins()
            for coin in active_coins:
                # Update market data, social metrics, etc.
                self.trade_manager.update_coin_metrics(coin)
        except Exception as e:
            logger.error(f"Error updating coin statuses: {e}")

    def _cleanup_old_data(self):
        """Clean up old data from database."""
        try:
            self.db_manager.cleanup_old_trades()
            self.db_manager.cleanup_old_historical_data()
        except Exception as e:
            logger.error(f"Error cleaning up data: {e}")

    def _perform_health_checks(self):
        """Perform system health checks."""
        try:
            # Check Solana connection
            if not self.solana_client.is_connected():
                logger.warning("Solana client disconnected, attempting reconnect...")
                self.solana_client.reconnect()

            # Check database connection
            self.db_manager.health_check()

        except Exception as e:
            logger.error(f"Health check failed: {e}")

    def stop(self):
        """Stop all background tasks and cleanup."""
        self.is_running = False
        logger.info("Shutting down background tasks...")


# Global app manager instance
app_manager = AppManager()


def create_app():
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(Config)
    app.secret_key = Config.SECRET_KEY or os.urandom(24)

    # Initialize database
    try:
        app_manager.db_manager.init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

    # Register routes
    register_routes(app)

    # Register error handlers
    register_error_handlers(app)

    app_manager.app = app
    return app


def register_routes(app):
    """Register all application routes."""

    @app.route('/')
    def index():
        """Main dashboard."""
        try:
            active_coins = app_manager.db_manager.get_active_coins()
            recent_trades = app_manager.db_manager.get_recent_trades(limit=10)
            system_stats = get_system_stats()

            return render_template('index.html',
                                   coins=active_coins,
                                   recent_trades=recent_trades,
                                   system_stats=system_stats)
        except Exception as e:
            logger.error(f"Error in index route: {e}")
            flash(f"Error loading dashboard: {str(e)}", 'error')
            return render_template('index.html', coins=[], recent_trades=[], system_stats={})

    @app.route('/launch_coin', methods=['GET', 'POST'])
    def launch_coin():
        """Launch new coin interface."""
        if request.method == 'POST':
            try:
                # Validate form data
                form_data = validate_launch_form(request.form)
                if not form_data['valid']:
                    flash(form_data['error'], 'error')
                    return redirect(url_for('launch_coin'))

                # Start coin launch in background
                threading.Thread(
                    target=launch_coin_async,
                    args=(form_data['data'],),
                    daemon=True
                ).start()

                flash('Coin launch initiated! Check the dashboard for updates.', 'success')
                return redirect(url_for('index'))

            except Exception as e:
                logger.error(f"Error launching coin: {e}")
                flash(f"Launch failed: {str(e)}", 'error')
                return redirect(url_for('launch_coin'))

        # GET request - show form with AI suggestions
        try:
            ai_suggestions = generate_ai_suggestions()
            return render_template('launch_coin.html', ai_suggestions=ai_suggestions)
        except Exception as e:
            logger.error(f"Error generating AI suggestions: {e}")
            return render_template('launch_coin.html', ai_suggestions={})

    @app.route('/coin/<mint_address>')
    def coin_details(mint_address):
        """Detailed view of specific coin."""
        try:
            coin = app_manager.db_manager.get_coin_by_mint(mint_address)
            if not coin:
                flash('Coin not found', 'error')
                return redirect(url_for('index'))

            trades = app_manager.db_manager.get_trades_for_coin(coin.id, limit=50)
            historical_data = app_manager.db_manager.get_historical_data(coin.id, hours=24)
            social_metrics = get_social_metrics(coin)

            return render_template('coin_details.html',
                                   coin=coin,
                                   trades=trades,
                                   historical_data=historical_data,
                                   social_metrics=social_metrics)
        except Exception as e:
            logger.error(f"Error in coin details: {e}")
            flash(f"Error loading coin details: {str(e)}", 'error')
            return redirect(url_for('index'))

    @app.route('/api/coins')
    def api_coins():
        """API endpoint for coins data."""
        try:
            coins = app_manager.db_manager.get_active_coins()
            return jsonify({
                'success': True,
                'data': [coin.to_dict() for coin in coins],
                'timestamp': datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"API error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/trades/<mint_address>')
    def api_trades(mint_address):
        """API endpoint for coin trades."""
        try:
            coin = app_manager.db_manager.get_coin_by_mint(mint_address)
            if not coin:
                return jsonify({'success': False, 'error': 'Coin not found'}), 404

            trades = app_manager.db_manager.get_trades_for_coin(coin.id, limit=100)
            return jsonify({
                'success': True,
                'data': [trade.to_dict() for trade in trades],
                'timestamp': datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"API error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/launch_status/<launch_id>')
    def api_launch_status(launch_id):
        """Check launch status."""
        try:
            status = app_manager.db_manager.get_launch_status(launch_id)
            return jsonify({
                'success': True,
                'data': status,
                'timestamp': datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"API error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/system_health')
    def api_system_health():
        """System health check endpoint."""
        try:
            health = {
                'solana_connected': app_manager.solana_client.is_connected(),
                'database_healthy': app_manager.db_manager.health_check(),
                'websocket_running': app_manager.is_running,
                'active_coins': len(app_manager.db_manager.get_active_coins()),
                'timestamp': datetime.utcnow().isoformat()
            }
            return jsonify({'success': True, 'data': health})
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


def register_error_handlers(app):
    """Register error handlers."""

    @app.errorhandler(404)
    def not_found(error):
        return render_template('error.html', error="Page not found"), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return render_template('error.html', error="Internal server error"), 500


def validate_launch_form(form_data):
    """Validate coin launch form data."""
    try:
        required_fields = ['name', 'symbol', 'description', 'initial_sol_amount']
        for field in required_fields:
            if not form_data.get(field):
                return {'valid': False, 'error': f'{field} is required'}

        # Validate SOL amount
        try:
            sol_amount = float(form_data['initial_sol_amount'])
            if sol_amount <= 0:
                return {'valid': False, 'error': 'SOL amount must be positive'}
        except ValueError:
            return {'valid': False, 'error': 'Invalid SOL amount'}

        return {
            'valid': True,
            'data': {
                'name': form_data['name'].strip(),
                'symbol': form_data['symbol'].strip().upper(),
                'description': form_data['description'].strip(),
                'image_url': form_data.get('image_url', '').strip(),
                'initial_sol_amount': sol_amount
            }
        }

    except Exception as e:
        return {'valid': False, 'error': str(e)}


def launch_coin_async(form_data):
    """Launch coin asynchronously."""
    try:
        app_manager.launch_manager.launch_new_coin(
            name=form_data['name'],
            symbol=form_data['symbol'],
            description=form_data['description'],
            image_url=form_data.get('image_url'),
            initial_sol_amount=form_data['initial_sol_amount']
        )
    except Exception as e:
        logger.error(f"Async coin launch error: {e}")


def generate_ai_suggestions():
    """Generate AI suggestions for coin launch."""
    try:
        suggestions = {
            'names': app_manager.ai_client.generate_text(
                "Generate 5 catchy, unique meme coin names. Return only the names, one per line."
            ).strip().split('\n')[:5],
            'descriptions': app_manager.ai_client.generate_text(
                "Generate 3 short, engaging descriptions for meme coins (50 words each). Return only descriptions, one per line."
            ).strip().split('\n')[:3],
            'social_posts': app_manager.ai_client.generate_text(
                "Generate 3 Twitter posts announcing a new meme coin launch. Keep under 280 characters each."
            ).strip().split('\n')[:3]
        }
        return suggestions
    except Exception as e:
        logger.error(f"Error generating AI suggestions: {e}")
        return {'names': [], 'descriptions': [], 'social_posts': []}


def get_system_stats():
    """Get system statistics."""
    try:
        return {
            'total_coins': app_manager.db_manager.get_total_coins(),
            'active_coins': len(app_manager.db_manager.get_active_coins()),
            'total_trades': app_manager.db_manager.get_total_trades(),
            'system_uptime': datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        return {}


def get_social_metrics(coin):
    """Get social media metrics for a coin."""
    try:
        return app_manager.social_media_manager.get_coin_metrics(coin.symbol)
    except Exception as e:
        logger.error(f"Error getting social metrics: {e}")
        return {}


# Create the Flask app
app = create_app()

if __name__ == '__main__':
    try:
        # Start background tasks
        app_manager.start_background_tasks()

        # Run the Flask app
        app.run(
            debug=Config.DEBUG,
            host=Config.HOST or '0.0.0.0',
            port=Config.PORT or 5000,
            threaded=True
        )

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Application error: {e}")
    finally:
        app_manager.stop()
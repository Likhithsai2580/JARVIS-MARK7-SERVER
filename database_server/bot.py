import sys
import os
from dotenv import load_dotenv
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, Dict
import asyncio
import logging
import base64
import io

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class DatabaseBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        super().__init__(
            command_prefix="!",  # Keeping prefix for legacy support
            intents=intents,
            help_command=None  # Removing default help as we'll use slash commands
        )
        self.channel_cache: Dict[str, discord.TextChannel] = {}
        
    async def setup_hook(self):
        await self.add_cog(DatabaseCommands(self))
        # Sync commands with Discord
        logger.info("Syncing commands with Discord...")
        await self.tree.sync()
        logger.info("Commands synced successfully!")

    async def get_channel_by_name(self, channel_name: str) -> discord.TextChannel:
        """Get Discord channel by name from cache or fetch it"""
        if channel_name in self.channel_cache:
            return self.channel_cache[channel_name]
        
        for guild in self.guilds:
            channel = discord.utils.get(guild.channels, name=channel_name)
            if channel:
                self.channel_cache[channel_name] = channel
                return channel
        
        raise ValueError(f"Channel {channel_name} not found")

    async def send_log(self, level: str, message: str, source: str):
        """Send a log message to the logs channel"""
        channel = await self.get_channel_by_name('logs')
        embed = discord.Embed(
            title=f"Log Entry from {source}",
            color=discord.Color.blue() if level == "INFO" else discord.Color.yellow()
        )
        embed.add_field(name="Level", value=level, inline=True)
        embed.add_field(name="Source", value=source, inline=True)
        embed.add_field(name="Message", value=message, inline=False)
        embed.set_footer(text=f"Timestamp: {discord.utils.utcnow().isoformat()}")
        await channel.send(embed=embed)

    async def send_error(self, error_type: str, message: str, source: str, stack_trace: Optional[str] = None):
        """Send an error message to the errors channel"""
        channel = await self.get_channel_by_name('errors')
        embed = discord.Embed(
            title=f"Error Entry from {source}",
            color=discord.Color.red()
        )
        embed.add_field(name="Error Type", value=error_type, inline=True)
        embed.add_field(name="Source", value=source, inline=True)
        embed.add_field(name="Message", value=message, inline=False)
        if stack_trace:
            embed.add_field(name="Stack Trace", value=f"```{stack_trace}```", inline=False)
        embed.set_footer(text=f"Timestamp: {discord.utils.utcnow().isoformat()}")
        await channel.send(embed=embed)

    async def send_face_auth(self, user_id: str, image_data: str) -> str:
        """Send a face authentication message to the face-auth channel"""
        channel = await self.get_channel_by_name('face-auth')
        
        if not image_data:
            raise ValueError("Image data is required for face authentication")
            
        try:
            # Remove data URL prefix if present
            if "data:image/png;base64," in image_data:
                image_data = image_data.split("data:image/png;base64,")[1]
            
            try:
                # Decode base64 to bytes
                image_bytes = base64.b64decode(image_data)
            except Exception as e:
                raise ValueError(f"Invalid base64 image data: {str(e)}")
            
            # Create file object
            file = discord.File(
                fp=io.BytesIO(image_bytes),
                filename=f"face_auth_{user_id}.png"
            )
            
            # Send message with image and user_id in content
            message = await channel.send(
                content=f"JARVIS_USER_ID: {user_id}",
                file=file
            )
            return str(message.id)
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            raise ValueError(f"Failed to process image: {str(e)}")

    async def send_auth(self, username: str, email: str, password: str) -> str:
        """Send authentication details to authentication channel and return message ID"""
        channel = await self.get_channel_by_name('authentication')
        
        # Check for existing username or email
        async for message in channel.history(limit=None):
            if message.embeds:
                embed = message.embeds[0]
                for field in embed.fields:
                    if field.name == "Username" and field.value == username:
                        raise ValueError("Username already exists")
                    if field.name == "Email" and field.value == email:
                        raise ValueError("Email already exists")
        
        embed = discord.Embed(
            title="New User Authentication",
            color=discord.Color.blue()
        )
        embed.add_field(name="Username", value=username, inline=True)
        embed.add_field(name="Email", value=email, inline=True)
        embed.add_field(name="Password", value=password, inline=False)
        embed.set_footer(text=f"Timestamp: {discord.utils.utcnow().isoformat()}")
        
        message = await channel.send(embed=embed)
        return str(message.id)  # This will be the jarvis_user_id

    async def create_project_post(self, jarvis_user_id: str, name: str, description: str, status: str) -> str:
        """Create a post in projects forum channel"""
        channel = await self.get_channel_by_name('projects')
        if not isinstance(channel, discord.ForumChannel):
            raise ValueError("Projects channel must be a forum channel")
            
        # Check if thread for user already exists
        existing_thread = None
        active_threads = channel.threads
        for thread in active_threads:
            if thread.name == f"User: {jarvis_user_id}":
                existing_thread = thread
                break
                
        if not existing_thread:
            # Also check archived threads
            async for thread in channel.archived_threads():
                if thread.name == f"User: {jarvis_user_id}":
                    existing_thread = thread
                    break
                
        if not existing_thread:
            # Create new thread for user
            embed = discord.Embed(
                title=f"Projects for User: {jarvis_user_id}",
                description="List of all projects for this user",
                color=discord.Color.blue()
            )
            
            thread = await channel.create_thread(
                name=f"User: {jarvis_user_id}",
                content=f"Project thread for user {jarvis_user_id}",
                embed=embed,
                applied_tags=[],
                auto_archive_duration=10080  # 7 days
            )
            existing_thread = thread.thread
            
        # Create project message in the thread
        project_embed = discord.Embed(
            title=name,
            description=description,
            color=discord.Color.green()
        )
        project_embed.add_field(name="Status", value=status, inline=True)
        project_embed.add_field(name="Created By", value=jarvis_user_id, inline=True)
        project_embed.set_footer(text=f"Created at: {discord.utils.utcnow().isoformat()}")
        
        # Send project message in thread
        message = await existing_thread.send(embed=project_embed)
        return str(message.id)

    async def check_auth(self, identifier: str, password: str) -> Optional[str]:
        """Check authentication details in authentication channel
        Args:
            identifier: username or email
            password: user password
        Returns:
            jarvis_user_id if credentials match, None otherwise
        """
        try:
            channel = await self.get_channel_by_name('authentication')
            if not channel:
                logger.error("Authentication channel not found")
                return None
            
            async for message in channel.history(limit=None):
                if message.embeds:
                    embed = message.embeds[0]
                    stored_username = None
                    stored_email = None
                    stored_password = None
                    
                    # Extract stored credentials from embed fields
                    for field in embed.fields:
                        if field.name == "Username":
                            stored_username = field.value
                        elif field.name == "Email":
                            stored_email = field.value
                        elif field.name == "Password":
                            stored_password = field.value
                    
                    # Check if credentials match
                    if stored_password and stored_password == password:
                        if identifier == stored_username or identifier == stored_email:
                            return str(message.id)  # Return jarvis_user_id (message ID)
            
            return None  # No matching credentials found
            
        except Exception as e:
            logger.error(f"Error checking authentication: {str(e)}")
            return None

class DatabaseCommands(commands.Cog):
    def __init__(self, bot: DatabaseBot):
        self.bot = bot
        self.ctx_menu = app_commands.ContextMenu(
            name='User Info',
            callback=self.user_info_context_menu,
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def create_channel(self, guild: discord.Guild, category: discord.CategoryChannel, name: str, channel_type: Optional[discord.ChannelType] = None) -> discord.TextChannel:
        """Helper method to create a channel in the given category"""
        try:
            existing_channel = discord.utils.get(category.channels, name=name)
            if existing_channel:
                return existing_channel
            
            if channel_type == discord.ChannelType.forum:
                return await guild.create_forum(
                    name=name,
                    category=category
                )
            else:
                return await guild.create_text_channel(
                    name=name,
                    category=category
                )
        except discord.Forbidden:
            raise discord.Forbidden("Bot doesn't have permission to create channels")
        except Exception as e:
            raise Exception(f"Failed to create channel: {str(e)}")

    @app_commands.command(name="setup", description="Initialize the database channels (Admin only)")
    @app_commands.default_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need administrator permissions to run this command.", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            if not interaction.guild.me.guild_permissions.manage_channels:
                await interaction.followup.send("❌ Bot needs 'Manage Channels' permission to setup database channels.", ephemeral=True)
                return

            category_name = "database"
            existing_category = discord.utils.get(interaction.guild.categories, name=category_name)
            
            if existing_category:
                category = existing_category
            else:
                category = await interaction.guild.create_category(category_name)

            channels = {
                'logs': None,
                'authentication': None,
                'errors': None,
                'face-auth': None,
                'projects': discord.ChannelType.forum
            }

            created_channels = []
            for channel_name, channel_type in channels.items():
                channel = await self.create_channel(interaction.guild, category, channel_name, channel_type)
                created_channels.append(channel.name)

            await interaction.followup.send(f"""
✅ Database channels setup completed successfully!
Created category: #{category_name}
Created channels:
• #logs - For system logs
• #authentication - For auth-related events
• #errors - For error tracking
• #face-auth - For facial authentication
• #projects - Forum for project management
            """.strip())

        except discord.Forbidden:
            await interaction.followup.send("❌ Bot doesn't have sufficient permissions to create channels.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred: {str(e)}", ephemeral=True)
            logger.error(f"Error in setup command: {str(e)}")

    @app_commands.command(name="ping", description="Check if the bot is responsive")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message("🏓 Pong!", ephemeral=True)

    @app_commands.command(name="reset", description="Reset all database channels by clearing their contents (Admin only)")
    @app_commands.default_permissions(administrator=True)
    async def reset(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need administrator permissions to run this command.", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            category = discord.utils.get(interaction.guild.categories, name="database")
            if not category:
                await interaction.followup.send("❌ Database category not found. Please run /setup first.", ephemeral=True)
                return

            channels = ['logs', 'authentication', 'errors', 'face-auth', 'projects']
            
            for channel_name in channels:
                channel = discord.utils.get(category.channels, name=channel_name)
                if channel:
                    try:
                        if isinstance(channel, discord.ForumChannel):
                            async for thread in channel.archived_threads():
                                try:
                                    await thread.delete()
                                    await asyncio.sleep(1)
                                except discord.errors.NotFound:
                                    continue
                            
                            for thread in channel.threads:
                                try:
                                    await thread.delete()
                                    await asyncio.sleep(1)
                                except discord.errors.NotFound:
                                    continue
                        else:
                            messages = []
                            async for message in channel.history(limit=None):
                                messages.append(message)
                                if len(messages) >= 100:
                                    try:
                                        await channel.delete_messages(messages)
                                        await asyncio.sleep(1)
                                    except discord.errors.HTTPException:
                                        for msg in messages:
                                            try:
                                                await msg.delete()
                                                await asyncio.sleep(0.5)
                                            except (discord.errors.NotFound, discord.errors.Forbidden):
                                                continue
                                    messages = []
                            
                            if messages:
                                try:
                                    await channel.delete_messages(messages)
                                except discord.errors.HTTPException:
                                    for msg in messages:
                                        try:
                                            await msg.delete()
                                            await asyncio.sleep(0.5)
                                        except (discord.errors.NotFound, discord.errors.Forbidden):
                                            continue
                        
                    except discord.Forbidden:
                        await interaction.followup.send(f"❌ Missing permissions for channel: #{channel_name}", ephemeral=True)
                        continue

            await interaction.followup.send("""
✅ Database reset completed successfully!
Cleared channels:
• #logs - System logs cleared
• #authentication - Auth records cleared
• #errors - Error logs cleared
• #face-auth - Face auth records cleared
• #projects - All project threads deleted
            """.strip())

        except discord.Forbidden:
            await interaction.followup.send("❌ Bot doesn't have sufficient permissions to reset channels.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred: {str(e)}", ephemeral=True)
            logger.error(f"Error in reset command: {str(e)}")

    async def user_info_context_menu(self, interaction: discord.Interaction, user: discord.Member):
        """Context menu command to show user information"""
        embed = discord.Embed(
            title=f"User Information - {user.name}",
            color=discord.Color.blue()
        )
        embed.add_field(name="ID", value=user.id, inline=True)
        embed.add_field(name="Joined At", value=user.joined_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        embed.add_field(name="Created At", value=user.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        embed.set_thumbnail(url=user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

# Create bot instance
bot = DatabaseBot()

async def start_bot():
    """Start the bot with the token from environment variables"""
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        raise ValueError("No Discord token found. Please set DISCORD_TOKEN in your .env file")
    
    try:
        await bot.start(token)
    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}")
        raise

if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        raise ValueError("No Discord token found. Please set DISCORD_TOKEN in your .env file")
    
    bot.run(token)